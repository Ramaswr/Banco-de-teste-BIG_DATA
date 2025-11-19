"""
Integration module: Streamlit ↔ Quantum ETL Engine
Module: etl_integrationUI.py

Purpose: Seamless Streamlit UI for launching and monitoring Quantum ETL jobs
"""

import streamlit as st
import subprocess
from pathlib import Path
from datetime import datetime
import psutil


def _logical_cpu_count() -> int:
    """Return a positive CPU count, falling back to 1 when psutil returns None."""
    count = psutil.cpu_count()
    return count if isinstance(count, int) and count > 0 else 1


def etl_dashboard():
    """Render ETL Dashboard in Streamlit."""
    
    st.markdown("""
    <div class="dashboard-header">
        <h1>⚡ Quantum ETL Engine Dashboard</h1>
        <p>Hybrid Binary/CSV/Parquet Ingestion with Amplitude-Estimation Analytics</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    logical_cores = _logical_cpu_count()
    with col1:
        st.metric("CPU Cores", logical_cores, "logical")
    with col2:
        ram_gb = psutil.virtual_memory().total / 1024 / 1024 / 1024
        st.metric("Total RAM", f"{ram_gb:.1f}GB")
    with col3:
        st.metric("Available RAM", f"{psutil.virtual_memory().available / 1024 / 1024 / 1024:.1f}GB")
    
    st.markdown("---")
    
    # Job configuration
    st.subheader("🔧 ETL Job Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        input_path = st.text_input(
            "📁 Input Path",
            value="./data",
            help="Directory with BIN/CSV files or single file path"
        )
        output_csv = st.text_input(
            "📄 Output CSV",
            value="./output/data.csv",
            help="Output CSV file path"
        )
        workers = st.slider(
            "👷 Worker Processes",
            min_value=1,
            max_value=logical_cores,
            value=max(1, logical_cores - 1),
            help="Number of parallel workers"
        )
    
    with col2:
        output_parquet = st.text_input(
            "📊 Output Parquet (optional)",
            value="./output/data.parquet",
            help="Optional Parquet output"
        )
        chunk_mb = st.slider(
            "💾 Chunk Size",
            min_value=16,
            max_value=512,
            value=64,
            step=16,
            help="Memory chunk size in MB"
        )
        sample_frac = st.select_slider(
            "🎲 Sample Fraction",
            options=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
            value=0.005,
            help="Fraction for analytics (smaller = faster)"
        )
    
    force_text = st.checkbox("🔤 Force Text Fallback", help="Skip BIN parsing, use CSV fallback")
    no_parquet = st.checkbox("⏭️ Skip Parquet", help="Don't convert to Parquet")
    
    # Run button
    st.markdown("---")
    
    if st.button("🚀 Launch ETL Pipeline", use_container_width=True):
        st.info("🚀 Starting Quantum ETL Pipeline...")
        
        # Build command
        cmd = [
            "python",
            "etl_batch/etl_core.py",
            "-i", input_path,
            "-o", output_csv,
            "-w", str(workers),
            "--chunk-bytes", str(chunk_mb * 1024 * 1024),
            "--sample-frac", str(sample_frac),
        ]
        
        if output_parquet:
            cmd.extend(["-p", output_parquet])
        if force_text:
            cmd.append("--force-text")
        if no_parquet:
            cmd.append("--no-parquet")
        
        try:
            # Run with real-time output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                st.success("✅ ETL Pipeline Completed Successfully!")
                
                # Show report if exists
                report_path = Path("report/etl_quantum_report.html")
                if report_path.exists():
                    st.markdown("### 📊 Quantum Report")
                    with open(report_path, "r", encoding="utf-8") as f:
                        st.markdown(f.read(), unsafe_allow_html=True)
                
                # Show audit log
                audit_log_path = Path(".secrets/etl_audit.log")
                if audit_log_path.exists():
                    with st.expander("📝 Audit Log"):
                        with open(audit_log_path, "r") as f:
                            st.code(f.read()[-2000:], language="log")  # Last 2000 chars
            else:
                st.error(f"❌ Pipeline Failed:\n{result.stderr}")
        
        except subprocess.TimeoutExpired:
            st.error("❌ Pipeline timeout (1 hour)")
        except Exception as e:
            st.error(f"❌ Error: {e}")
    
    # Latest reports
    st.markdown("---")
    st.subheader("📂 Recent Reports")
    
    report_dir = Path("report")
    if report_dir.exists():
        reports = sorted(report_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if reports:
            for report in reports[:5]:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"📄 {report.name}")
                with col2:
                    mtime = datetime.fromtimestamp(report.stat().st_mtime)
                    st.write(f"🕐 {mtime.strftime('%Y-%m-%d %H:%M')}")
                with col3:
                    if st.button("👁️ View", key=f"view_{report.name}"):
                        with open(report, "r") as f:
                            st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.info("No reports found yet. Run a job to generate one.")
    else:
        st.info("Report directory not found. Run a job to create it.")


if __name__ == "__main__":
    etl_dashboard()
