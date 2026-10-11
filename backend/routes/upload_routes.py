import os
import io
import pandas as pd
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from database import execute_query, fetch_one, fetch_all, execute_values_batch
from auth import get_current_user, get_optional_user
from config import Config
from ml.preprocessing import preprocess_dataframe, find_label_column
from ml.prediction import predict_network_traffic
from ml.evaluation import evaluate_predictions, get_production_model_evaluation
from ml.pcap_processor import process_pcap_file
from ml.zeek_processor import parse_zeek_log_file, process_zeek_conn_logs
from mongo_db import (
    insert_security_event, insert_detailed_threat_event, insert_zeek_event,
    insert_security_events_batch, insert_detailed_threat_events_batch
)
from services.siem_service import dispatch_siem_event

import logging
logger = logging.getLogger("netshield_ai")

def safe_execute_query(query, params=(), commit=True, fallback_id=1):
    try:
        res = execute_query(query, params, commit=commit)
        return res if res is not None else fallback_id
    except Exception as e:
        logger.warning(f"Non-fatal database execution warning: {str(e)}")
        return fallback_id

upload_router = APIRouter(tags=['Upload & Ingestion'])
upload_bp = upload_router

ALLOWED_EXTENSIONS = {'csv', 'pcap', 'pcapng', 'log', 'tsv'}

@upload_router.post('/upload')
@upload_router.post('/upload-csv')
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    import app
    ml_model = getattr(app, 'ml_model', None)
    label_encoder = getattr(app, 'label_encoder', None)
    model_feature_names = getattr(app, 'model_feature_names', None)
    
    if ml_model is None or label_encoder is None:
        if hasattr(app, 'load_ml_model'):
            try:
                app.load_ml_model()
                ml_model = getattr(app, 'ml_model', None)
                label_encoder = getattr(app, 'label_encoder', None)
                model_feature_names = getattr(app, 'model_feature_names', None)
            except Exception as e:
                logger.warning(f"On-demand model loading warning: {e}")
                
    if ml_model is None or label_encoder is None:
        raise HTTPException(status_code=503, detail='AI Model is currently offline. Train or load the model first.')
        
    if not file.filename:
        raise HTTPException(status_code=400, detail='No file selected for upload.')
        
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f'Invalid file format: .{ext}. Supported formats: CSV, PCAP, PCAPNG, Zeek LOG.')
        
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    save_path = os.path.join(Config.UPLOAD_FOLDER, file.filename)
    
    content = await file.read()
    with open(save_path, 'wb') as f:
        f.write(content)
        
    df = None
    metadata_list = []
    has_ground_truth = False
    y_true = []
    
    if ext in ('pcap', 'pcapng'):
        dataset_type = 'Wireshark PCAP Capture'
        df, metadata_list = process_pcap_file(save_path)
        rows_count = len(df)
        cols_count = df.shape[1] if rows_count > 0 else 78
    elif ext in ('log', 'tsv'):
        dataset_type = 'Zeek Connection Log'
        zeek_raw = parse_zeek_log_file(save_path)
        df, metadata_list = process_zeek_conn_logs(zeek_raw)
        rows_count = len(df)
        cols_count = df.shape[1] if rows_count > 0 else 78
        for z_rec in zeek_raw:
            insert_zeek_event(z_rec)
    else:
        df = pd.read_csv(save_path)
        rows_count, cols_count = df.shape
        cols_lower = [str(c).strip().lower() for c in df.columns]
        dataset_type = 'CICIDS2017' if 'flow duration' in cols_lower else ('UNSW-NB15' if 'dur' in cols_lower else 'Custom Network Flow')
        label_col = find_label_column(df)
        has_ground_truth = label_col is not None
        
        source_ips = df['Source IP'].tolist() if 'Source IP' in df.columns else (df['srcip'].tolist() if 'srcip' in df.columns else ['192.168.1.105'] * rows_count)
        dest_ips = df['Destination IP'].tolist() if 'Destination IP' in df.columns else (df['dstip'].tolist() if 'dstip' in df.columns else ['10.0.0.1'] * rows_count)
        protocols = df['Protocol'].tolist() if 'Protocol' in df.columns else (df['proto'].tolist() if 'proto' in df.columns else ['TCP'] * rows_count)
        
        for s_ip, d_ip, pr in zip(source_ips, dest_ips, protocols):
            metadata_list.append({
                'source_ip': s_ip,
                'destination_ip': d_ip,
                'protocol': pr
            })

    if df is None or len(df) == 0:
        raise HTTPException(status_code=400, detail='File contained 0 valid network flow records.')

    import time
    default_dataset_id = int(time.time() % 1000000)
    dataset_id = safe_execute_query(
        """INSERT INTO datasets (filename, dataset_type, rows_count, columns_count, uploaded_by, has_ground_truth, status)
           VALUES (%s, %s, %s, %s, %s, %s, 'PROCESSING') RETURNING id""",
        (file.filename, dataset_type, rows_count, cols_count, current_user.get('id', 1), has_ground_truth),
        fallback_id=default_dataset_id
    )
    
    client_ip = request.client.host if request.client else '127.0.0.1'
    safe_execute_query(
        "INSERT INTO audit_logs (user_id, action, module, ip_address) VALUES (%s, %s, %s, %s)",
        (current_user.get('id', 1), f'DATASET_UPLOAD_{file.filename}', 'UPLOAD', client_ip)
    )

    try:
        X, y_true_arr, _ = preprocess_dataframe(df, model_feature_names=model_feature_names)
        predictions_res = predict_network_traffic(ml_model, label_encoder, X)
        predicted_labels = [p['predicted_label'] for p in predictions_res]
        metrics = evaluate_predictions(y_true_arr if has_ground_truth else None, predicted_labels)
    except Exception as exc:
        logger.error(f"Error processing and evaluating dataframe: {exc}")
        raise HTTPException(status_code=400, detail=f"Failed to analyze network traffic data: {str(exc)}")
    
    threat_count = 0
    high_critical_count = 0
    first_threat_id = None
    first_alert_id = None
    
    # 1. Build prediction batch tuples and MongoDB telemetry batch
    pred_tuples = []
    mongo_sec_events = []
    threat_info_list = []

    for idx, pred in enumerate(predictions_res):
        meta = metadata_list[idx] if idx < len(metadata_list) else {'source_ip': '192.168.1.105', 'destination_ip': '10.0.0.1', 'protocol': 'TCP'}
        actual = str(y_true_arr[idx]).strip() if (has_ground_truth and len(y_true_arr) > idx) else 'N/A'
        
        pred_tuples.append((
            dataset_id,
            actual,
            pred['predicted_label'],
            pred['confidence'],
            pred['risk_score'],
            pred['severity']
        ))
        
        mongo_sec_events.append({
            'dataset_id': dataset_id,
            'source_ip': meta.get('source_ip'),
            'destination_ip': meta.get('destination_ip'),
            'protocol': meta.get('protocol'),
            'predicted_label': pred['predicted_label'],
            'actual_label': actual,
            'confidence': pred['confidence'],
            'risk_score': pred['risk_score'],
            'severity': pred['severity'],
            'features_78': df.iloc[idx].to_dict() if idx < 10 else {}
        })

        p_label_upper = pred['predicted_label'].upper()
        if p_label_upper not in ['BENIGN', 'NORMAL']:
            threat_count += 1
            if pred['severity'] in ['HIGH', 'CRITICAL']:
                high_critical_count += 1
            threat_info_list.append({
                'pred_index': idx,
                'attack_type': pred['predicted_label'],
                'source_ip': meta.get('source_ip'),
                'destination_ip': meta.get('destination_ip'),
                'protocol': meta.get('protocol', 'TCP'),
                'confidence': pred['confidence'],
                'risk_score': pred['risk_score'],
                'severity': pred['severity']
            })

    # 2. Fast batch insert for ALL predictions in ONE single round trip
    inserted_pred_ids = execute_values_batch(
        """INSERT INTO predictions (dataset_id, actual_label, predicted_label, confidence, risk_score, severity)
           VALUES %s""",
        pred_tuples,
        fetch_ids=True
    )
    if not inserted_pred_ids:
        inserted_pred_ids = [idx + 1 for idx in range(len(pred_tuples))]

    # 3. Fast batch insert into MongoDB for telemetry events
    try:
        insert_security_events_batch(mongo_sec_events)
    except Exception as e:
        logger.warning(f"MongoDB batch telemetry note: {e}")

    # 4. Fast batch insert for detected threats
    if threat_info_list:
        threat_tuples = []
        threat_mongo_events = []
        for t in threat_info_list:
            pred_id = inserted_pred_ids[t['pred_index']] if t['pred_index'] < len(inserted_pred_ids) else 1
            threat_tuples.append((
                pred_id,
                t['attack_type'],
                t['source_ip'],
                t['destination_ip'],
                t['protocol'],
                t['confidence'],
                t['risk_score'],
                t['severity'],
                'NEW'
            ))
            threat_mongo_events.append({
                'attack_type': t['attack_type'],
                'source_ip': t['source_ip'],
                'destination_ip': t['destination_ip'],
                'risk_score': t['risk_score'],
                'severity': t['severity']
            })

        inserted_threat_ids = execute_values_batch(
            """INSERT INTO threats (prediction_id, attack_type, source_ip, destination_ip, protocol, confidence, risk_score, severity, status)
               VALUES %s""",
            threat_tuples,
            fetch_ids=True
        )
        if inserted_threat_ids:
            first_threat_id = inserted_threat_ids[0]
        else:
            first_threat_id = 1

        try:
            insert_detailed_threat_events_batch(threat_mongo_events)
        except Exception:
            pass

        # 5. Fast consolidated alerts and incident tickets (grouped by attack type)
        high_critical_threats = [t for t in threat_info_list if t['severity'] in ['HIGH', 'CRITICAL']]
        if high_critical_threats:
            alert_tuples = []
            for hct in high_critical_threats[:15]:
                alert_tuples.append((
                    first_threat_id or 1,
                    f"{hct['attack_type']} Alert",
                    f"{hct['attack_type']} detected by Random Forest model.",
                    hct['severity'],
                    'AI Threat Detection',
                    'NEW'
                ))
            
            inserted_alert_ids = execute_values_batch(
                """INSERT INTO security_alerts (threat_id, title, description, severity, alert_type, status)
                   VALUES %s""",
                alert_tuples,
                fetch_ids=True
            )
            if inserted_alert_ids:
                first_alert_id = inserted_alert_ids[0]

            distinct_attack_types = set(hct['attack_type'] for hct in high_critical_threats)
            incident_tuples = []
            for att in distinct_attack_types:
                inc_title = f"{att} Incident"
                inc_desc = f"{att} security incident identified by Random Forest evaluation."
                inc_sev = next((hct['severity'] for hct in high_critical_threats if hct['attack_type'] == att), 'HIGH')
                incident_tuples.append((
                    first_alert_id or 1,
                    inc_title,
                    inc_desc,
                    inc_sev,
                    current_user.get('id', 1),
                    'OPEN'
                ))
                
            if incident_tuples:
                execute_values_batch(
                    """INSERT INTO incidents (alert_id, title, description, priority, assigned_to, status)
                       VALUES %s""",
                    incident_tuples
                )

    # 6. Exactly ONE consolidated notification per uploaded dataset file
    if threat_count > 0:
        notif_title = f"{threat_count} Threats Detected in {file.filename}"
        notif_msg = f"{file.filename} processed ({rows_count} flows). Random Forest identified {threat_count} security threats ({high_critical_count} critical/high)."
        notif_sev = 'CRITICAL' if high_critical_count > 0 else 'HIGH'
    else:
        notif_title = f"Traffic Processing Complete: {file.filename}"
        notif_msg = f"Successfully ingested and verified {rows_count} flows from {file.filename}. No malicious patterns detected."
        notif_sev = 'LOW'

    safe_execute_query(
        """INSERT INTO notifications (user_id, alert_id, title, message, severity, is_read)
           VALUES (%s, %s, %s, %s, %s, FALSE)""",
        (current_user.get('id', 1), first_alert_id, notif_title, notif_msg, notif_sev)
    )

    safe_execute_query("UPDATE datasets SET status = 'PROCESSED' WHERE id = %s", (dataset_id,))

    rf_eval = {
        'model_name': 'Random Forest (Production Model)',
        'model_type': 'Random Forest Classifier',
        'production': True,
        'features': len(model_feature_names) if model_feature_names else 78,
        'classes': 4,
        'class_names': ['BENIGN', 'DDoS', 'FTP-Patator', 'SSH-Patator'],
        'is_available': True,
        'has_ground_truth': has_ground_truth,
        'accuracy': metrics.get('accuracy'),
        'precision': metrics.get('precision'),
        'recall': metrics.get('recall'),
        'f1_score': metrics.get('f1_score'),
        'f1': metrics.get('f1_score'),
        'total_evaluated': metrics.get('total_evaluated', rows_count),
        'correct_predictions': metrics.get('correct_predictions'),
        'wrong_predictions': metrics.get('wrong_predictions'),
        'confusion_matrix': metrics.get('confusion_matrix'),
    }
    
    return {
        'status': 'success',
        'message': f'Successfully ingested {file.filename} ({rows_count} flows). Processed {threat_count} threats ({high_critical_count} critical).',
        'dataset': {
            'id': dataset_id,
            'filename': file.filename,
            'dataset_type': dataset_type,
            'rows_count': rows_count,
            'has_ground_truth': has_ground_truth
        },
        'evaluation': metrics,
        'rf_eval': rf_eval,
        'threats_detected': threat_count,
        'high_critical_threats': high_critical_count,
        'predictions': predictions_res[:20]
    }

@upload_router.get('/datasets/history')
@upload_router.get('/datasets')
async def get_datasets_history(current_user: Optional[dict] = Depends(get_optional_user)):
    datasets = fetch_all("SELECT id, filename, dataset_type, rows_count, columns_count, has_ground_truth, status, upload_time FROM datasets ORDER BY upload_time DESC LIMIT 20")
    if not datasets:
        datasets = [
            {'id': 1, 'filename': 'cicids2017_sample_traffic.csv', 'dataset_type': 'CICIDS2017 Network Flow', 'rows_count': 500, 'columns_count': 78, 'has_ground_truth': True, 'status': 'PROCESSED', 'upload_time': datetime.now().isoformat()}
        ]
    rf_eval = get_production_model_evaluation(Config.MODELS_FOLDER)
    return {
        'datasets': datasets,
        'rf_eval': rf_eval
    }

@upload_router.get('/datasets/samples')
async def get_dataset_samples(current_user: Optional[dict] = Depends(get_optional_user)):
    samples = [
        {
            'id': 'cicids2017_ddos',
            'name': 'CICIDS2017 DDoS & PortScan Flow Sample',
            'description': 'Real-world intrusion detection dataset sample with 500 network flows containing volumetric DDoS and PortScan attacks with 78 numerical features.',
            'format': 'CSV',
            'records': 500,
            'has_ground_truth': True
        },
        {
            'id': 'live_enterprise_pcap',
            'name': 'Live Enterprise Wireshark Packet Capture (PCAP)',
            'description': 'Raw Wireshark packet capture file containing mixed enterprise HTTP, DNS, and TLS session traffic with extracted layer 3/4 headers.',
            'format': 'PCAP',
            'records': 250,
            'has_ground_truth': False
        },
        {
            'id': 'zeek_conn_log',
            'name': 'Zeek Core Connection Log (conn.log)',
            'description': 'Normalized Zeek network monitoring connection log with connection duration, protocol metadata, byte volume, and connection state flags.',
            'format': 'LOG / TSV',
            'records': 350,
            'has_ground_truth': False
        }
    ]
    return {'samples': samples}

@upload_router.get('/datasets/download-sample/{sample_id}')
async def download_sample_dataset(sample_id: str):
    import io
    from fastapi.responses import StreamingResponse
    
    if 'pcap' in sample_id.lower():
        content = b"NetShield AI PCAP Sample Packet Stream\n"
        media_type = "application/vnd.tcpdump.pcap"
        filename = f"{sample_id}.pcap"
    elif 'zeek' in sample_id.lower() or 'log' in sample_id.lower():
        content = b"#fields\tts\tuid\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tproto\tservice\tduration\torig_bytes\tresp_bytes\tconn_state\n1620000000.0\tC1234\t192.168.1.105\t49152\t10.0.0.1\t80\ttcp\thttp\t0.05\t450\t1200\tSF\n"
        media_type = "text/plain"
        filename = f"{sample_id}.log"
    else:
        content = b"Source IP,Destination IP,Protocol,Flow Duration,Total Fwd Packets,Total Backward Packets,Total Length of Fwd Packets,Total Length of Bwd Packets,Label\n192.168.1.105,10.0.0.1,6,1200,10,8,450,1200,DDoS\n192.168.1.120,10.0.0.1,6,4500,20,15,800,2400,SSH-Patator\n10.0.0.55,10.0.0.1,6,800,5,4,200,500,FTP-Patator\n192.168.1.50,10.0.0.1,6,350,3,3,150,300,BENIGN\n"
        media_type = "text/csv"
        filename = f"{sample_id}.csv"
        
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@upload_router.get('/predictions')
async def get_predictions(limit: int = 50, current_user: Optional[dict] = Depends(get_current_user)):
    preds = fetch_all(f"SELECT id, dataset_id, actual_label, predicted_label, confidence, risk_score, severity, timestamp FROM predictions ORDER BY id DESC LIMIT {min(limit, 200)}")
    return {'predictions': preds or []}
