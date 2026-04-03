import pandas as pd
import json, os
from datetime import datetime

class DataAnalyst:
    
    async def analyze_csv(self, path: str) -> str:
        """Analyze CSV file and return insights."""
        try:
            expanded = os.path.expanduser(path)
            df = pd.read_csv(expanded)
            
            # Basic stats
            rows, cols = df.shape
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            stats = {
                "rows": rows,
                "columns": cols,
                "column_names": df.columns.tolist(),
                "numeric_columns": numeric_cols,
                "missing_values": df.isnull().sum().to_dict(),
                "summary": {}
            }
            
            # Stats for numeric cols
            for col in numeric_cols[:5]:
                stats["summary"][col] = {
                    "mean": round(float(df[col].mean()), 2),
                    "min": round(float(df[col].min()), 2),
                    "max": round(float(df[col].max()), 2),
                    "std": round(float(df[col].std()), 2)
                }
            
            # Ask LLM for insights
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from llm import _chat
                prompt = (
                    f"Analyze this CSV data and provide insights:\n"
                    f"{json.dumps(stats, indent=2)}\n\n"
                    f"Give 3-5 key insights and recommendations."
                )
                insights = _chat(system="You are an expert Data Analyst.", user=prompt)
            except Exception as e:
                insights = f"LLM analysis failed: {e}"
            
            return (
                f"📊 **Data Analysis**: {path}\n"
                f"Rows: {rows} | Cols: {cols}\n"
                f"Numeric: {', '.join(numeric_cols)}\n\n"
                f"{insights}"
            )
        except Exception as e:
            return f"Analysis failed: {e}"
    
    async def generate_chart(self, path: str, chart_type: str = "bar", x_col: str = None, y_col: str = None) -> str:
        """Generate chart from CSV data."""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            df = pd.read_csv(os.path.expanduser(path))
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            if not numeric_cols:
                return "No numeric columns found."
            
            y = y_col or numeric_cols[0]
            x = x_col or df.columns[0]
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_facecolor('#0a1a1a')
            fig.set_facecolor('#020d0d')
            ax.tick_params(colors='#00ffcc')
            ax.spines[:].set_color('#00ffcc')
            
            if chart_type == "bar":
                ax.bar(df[x][:20], df[y][:20], color='#00ffcc', alpha=0.8)
            elif chart_type == "line":
                ax.plot(df[x][:50], df[y][:50], color='#00ffcc', linewidth=2)
            elif chart_type == "scatter":
                ax.scatter(df[x][:100], df[y][:100], color='#00ffcc', alpha=0.6)
            
            ax.set_title(f"{y} by {x}", color='#00ffcc', fontsize=14)
            ax.set_xlabel(x, color='white')
            ax.set_ylabel(y, color='white')
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_path = os.path.expanduser(f"~/Desktop/nova_chart_{ts}.png")
            plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='#020d0d')
            plt.close()
            
            import subprocess
            subprocess.Popen(['open', chart_path])
            
            return f"Chart saved: {chart_path}"
        except Exception as e:
            return f"Chart failed: {e}"

data_analyst = DataAnalyst()
