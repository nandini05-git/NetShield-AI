import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

LABEL_COLUMN_CANDIDATES = ['label', 'attack_cat', 'target', 'class', 'attack_type', 'category']

SRC_IP_CANDIDATES = ['source ip', 'src ip', 'srcip', 'source_ip', 'src_ip']
DST_IP_CANDIDATES = ['destination ip', 'dst ip', 'dstip', 'destination_ip', 'dst_ip']
PROTO_CANDIDATES = ['protocol', 'proto', 'protocol_name']

def find_candidate_column(df, candidates):
    cols_map = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate in cols_map:
            return cols_map[candidate]
    return None

def find_label_column(df):
    return find_candidate_column(df, LABEL_COLUMN_CANDIDATES)

def clean_column_names(df):
    df.columns = df.columns.str.strip()
    return df

def preprocess_dataframe(df, model_feature_names=None):
    """
    Preprocesses uploaded network dataset DataFrame for ML model inference:
    1. Cleans and normalizes column names
    2. Identifies ground truth label column if available
    3. Handles infinite / missing values
    4. Validates required model features and returns missing features error if incomplete
    5. Converts numeric values to float32
    """
    df = clean_column_names(df.copy())
    
    label_col = find_label_column(df)
    y_true = None
    
    if label_col:
        y_true = df[label_col].astype(str).str.strip().tolist()
        df = df.drop(columns=[label_col])
    
    # Normalize IP & Protocol metadata columns
    src_ip_col = find_candidate_column(df, SRC_IP_CANDIDATES)
    dst_ip_col = find_candidate_column(df, DST_IP_CANDIDATES)
    proto_col = find_candidate_column(df, PROTO_CANDIDATES)

    # Drop non-numeric metadata columns unless present in model expected features
    meta_cols = [src_ip_col, dst_ip_col, proto_col, 'Flow ID', 'Timestamp', 'timestamp']
    existing_meta = [c for c in meta_cols if c and c in df.columns and (model_feature_names is None or c not in model_feature_names)]
    if existing_meta:
        df = df.drop(columns=existing_meta)

    # Check and align required model features
    if model_feature_names is not None:
        col_mapping = {str(c).strip().lower(): c for c in df.columns}
        
        # Align existing columns with case-insensitive matching
        for feat in model_feature_names:
            feat_lower = str(feat).strip().lower()
            if feat not in df.columns and feat_lower in col_mapping:
                df[feat] = df[col_mapping[feat_lower]]
            elif feat not in df.columns:
                df[feat] = 0.0
                
        df = df[model_feature_names]

    # Convert remaining columns to numeric float32
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.fillna(0.0)
    
    X = df.astype(np.float32)
    return X, y_true, (label_col is not None)
