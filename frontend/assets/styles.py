"""Centralized CSS styles for the WhatYouSaid UI."""

TABLE_CSS = """<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    .main { 
        font-family: 'Inter', sans-serif; 
        background-color: #121212;
    }

    /* Set background for the entire main container */
    [data-testid="stAppViewContainer"] {
        background-color: #121212;
    }

    /* Ensure tabs and dashboard area also use the same background */
    [data-testid="stMain"] {
        background-color: #121212;
    }
    
    .content-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        background: transparent;
    }
    
    .content-table th {
        text-align: left;
        padding: 12px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        color: #9aa4ad;
        font-weight: 500;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .content-table td {
        padding: 16px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        vertical-align: middle;
    }
    
    .content-table tr:hover {
        background: rgba(255,255,255,0.02);
    }
    
    .source-info {
        display: flex;
        flex-direction: column;
    }
    
    .source-title {
        font-weight: 500;
        color: #e6eef7;
        font-size: 0.9rem;
        text-decoration: none !important;
        margin-bottom: 2px;
    }
    
    .source-sub {
        color: #6a737d;
        font-size: 0.7rem;
    }
    
    .meta-text {
        color: #9aa4ad;
        font-size: 0.8rem;
    }
    
    /* Modern Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 600;
        display: inline-block;
        text-transform: capitalize;
        white-space: nowrap;
    }
    .badge-done { background: rgba(16,185,129,0.1); color: #10b981; border: 1px solid rgba(16,185,129,0.2); }
    .badge-processing { background: rgba(59,130,246,0.1); color: #3b82f6; border: 1px solid rgba(59,130,246,0.2); }
    .badge-pending { background: rgba(245,158,11,0.1); color: #f59e0b; border: 1px solid rgba(245,158,11,0.2); }
    .badge-error, .badge-failed { background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.2); }
    .badge-active { background: rgba(139,92,246,0.1); color: #8b5cf6; border: 1px solid rgba(139,92,246,0.2); }
    
    .action-dots {
        color: #4b5563;
        font-size: 1.1rem;
        text-align: right;
    }
    
    /* Task Cards for Ingestion History */
    .task-card {
        background-color: #121212;
        border: 1px solid #27272a;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 8px;
    }

    /* Chunk Cards */
    .chunk-card {
        background-color: #121212;
        border: 1px solid #27272a;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .chunk-header { 
        display: flex; 
        justify-content: space-between; 
        margin-bottom: 12px; 
        align-items: center;
    }
    .chunk-title { color: white; font-weight: bold; font-size: 14px; }
    .chunk-meta { 
        background: #18181b; 
        color: #71717a; 
        font-size: 10px; 
        padding: 2px 8px; 
        border-radius: 4px; 
        border: 1px solid #27272a; 
        margin-left: 8px;
    }
    .chunk-content { color: #a1a1aa; font-size: 14px; line-height: 1.6; }

    /* Fixed Header and Scrollable Content logic */
    [data-testid="stHeader"] {
        background-color: rgba(14, 17, 23, 0.8);
        backdrop-filter: blur(10px);
    }

    /* Target the tabs container to make it sticky */
    div[data-testid="stTabs"] [data-testid="stTabsHeader"] {
        position: sticky;
        top: 0;
        z-index: 1000;
        background-color: #0e1117;
        padding-top: 10px;
        margin-bottom: 10px;
    }

    /* Utility class for scrollable area if needed via st.html */
    .scrollable-content {
        height: calc(100vh - 180px);
        overflow-y: auto;
        padding-right: 10px;
    }
</style>"""
