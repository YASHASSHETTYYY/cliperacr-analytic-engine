import json
import logging
from typing import Dict, Any
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class AnalyticsEngine:
    def __init__(self, json_filepath: str):
        self.filepath = json_filepath
        self.records_dropped_invalid_ts = 0
        self.records_dropped_outlier_date = 0
        self.df = self._load_and_clean_data()

    def _load_and_clean_data(self) -> pd.DataFrame:
        """Loads dataset safely and handles malformed timestamps or JSON formatting errors."""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON file '{self.filepath}': {e}")
            raise
        except Exception as e:
            logging.error(f"Error reading file '{self.filepath}': {e}")
            raise

        df = pd.DataFrame(data)
        if df.empty:
            logging.warning("Loaded empty dataset.")
            return df

        initial_row_count = len(df)

        # Parse timestamps safely; invalid format entries become NaT
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
        
        valid_ts_df = df.dropna(subset=['timestamp']).copy()
        self.records_dropped_invalid_ts = initial_row_count - len(valid_ts_df)

        # Enforce realistic date range boundaries (2020 to 2026)
        min_bound = pd.Timestamp('2020-01-01T00:00:00Z')
        max_bound = pd.Timestamp('2026-12-31T23:59:59Z')
        
        cleaned_df = valid_ts_df[
            (valid_ts_df['timestamp'] >= min_bound) & 
            (valid_ts_df['timestamp'] <= max_bound)
        ].copy()
        
        self.records_dropped_outlier_date = len(valid_ts_df) - len(cleaned_df)

        # Log audit details
        logging.info(f"Ingestion Audit: {initial_row_count} total raw rows.")
        logging.info(f"Dropped {self.records_dropped_invalid_ts} record(s) due to invalid/corrupted timestamps.")
        logging.info(f"Dropped {self.records_dropped_outlier_date} record(s) due to out-of-bounds dates.")
        logging.info(f"Retained {len(cleaned_df)} valid record(s) for processing.")

        # Extract device property safely
        if 'properties' in cleaned_df.columns:
            cleaned_df['device'] = cleaned_df['properties'].apply(
                lambda x: x.get('device') if isinstance(x, dict) else None
            )
        else:
            cleaned_df['device'] = None

        return cleaned_df

    def get_daily_active_users(self) -> Dict[str, int]:
        """Calculates Daily Active Users (DAU)."""
        valid_users = self.df.dropna(subset=['user_id']).copy()
        valid_users['date'] = valid_users['timestamp'].dt.strftime('%Y-%m-%d')
        dau = valid_users.groupby('date')['user_id'].nunique().to_dict()
        return dau

    def get_session_metrics(self) -> Dict[str, Any]:
        """Calculates total sessions, unique users, and average sessions per user."""
        valid_sessions = self.df.dropna(subset=['session_id'])
        total_sessions = int(valid_sessions['session_id'].nunique())
        unique_users = int(valid_sessions['user_id'].dropna().nunique())
        avg_sessions = round(total_sessions / unique_users, 2) if unique_users > 0 else 0.0

        return {
            "total_sessions": total_sessions,
            "unique_users": unique_users,
            "avg_sessions_per_user": avg_sessions
        }

    def get_average_session_duration(self) -> float:
        """Calculates average session duration in seconds."""
        valid_sessions = self.df.dropna(subset=['session_id'])
        if valid_sessions.empty:
            return 0.0
        session_times = valid_sessions.groupby('session_id')['timestamp'].agg(['min', 'max'])
        session_times['duration'] = (session_times['max'] - session_times['min']).dt.total_seconds()
        return round(float(session_times['duration'].mean()), 2)

    def get_top_interactions(self, top_n: int = 5) -> Dict[str, int]:
        """Calculates top clicked interactions."""
        clicks = self.df[(self.df['event_name'] == 'interaction_click') & (self.df['interaction_id'].notna())]
        top = clicks['interaction_id'].value_counts().head(top_n).to_dict()
        return top

    def get_bounce_rate(self) -> float:
        """Calculates bounce rate (% of sessions with only 1 event OR 0 duration)."""
        valid_sessions = self.df.dropna(subset=['session_id'])
        if valid_sessions.empty:
            return 0.0
            
        session_stats = valid_sessions.groupby('session_id').agg(
            event_count=('event_id', 'count'),
            min_ts=('timestamp', 'min'),
            max_ts=('timestamp', 'max')
        )
        
        bounces = session_stats[
            (session_stats['event_count'] == 1) | 
            (session_stats['min_ts'] == session_stats['max_ts'])
        ]
        
        total_sessions = len(session_stats)
        bounce_rate = (len(bounces) / total_sessions * 100) if total_sessions > 0 else 0.0
        return round(bounce_rate, 2)

    def get_conversion_rate(self) -> float:
        """Calculates conversion rate (% of sessions containing a 'purchase' event)."""
        valid_sessions = self.df.dropna(subset=['session_id'])
        total_sessions = valid_sessions['session_id'].nunique()
        if total_sessions == 0:
            return 0.0
            
        converted_sessions = valid_sessions[valid_sessions['event_name'] == 'purchase']['session_id'].nunique()
        conv_rate = (converted_sessions / total_sessions * 100)
        return round(conv_rate, 2)

    def get_device_share(self) -> Dict[str, float]:
        """Additional Metric: Percentage distribution of total events across devices."""
        device_counts = self.df['device'].dropna().value_counts(normalize=True) * 100
        return {k: round(v, 2) for k, v in device_counts.to_dict().items()}

    def run_self_verification(self) -> bool:
        """Performs sanity checks on calculated outputs."""
        session_info = self.get_session_metrics()
        bounce_rate = self.get_bounce_rate()
        conversion_rate = self.get_conversion_rate()
        dau = self.get_daily_active_users()

        assert session_info['total_sessions'] > 0, "Assertion Error: Total sessions must be positive."
        assert session_info['unique_users'] > 0, "Assertion Error: Unique users must be positive."
        assert 0.0 <= bounce_rate <= 100.0, "Assertion Error: Bounce rate out of bounds."
        assert 0.0 <= conversion_rate <= 100.0, "Assertion Error: Conversion rate out of bounds."
        assert all(count >= 0 for count in dau.values()), "Assertion Error: DAU counts must be non-negative."
        
        logging.info("Self-verification completed successfully. All metric invariants satisfied.")
        return True

    def generate_report(self):
        """Prints all required metrics in a clear format."""
        print("=" * 50)
        print("          CLIPERACT ANALYTICS ENGINE           ")
        print("=" * 50)
        print(f"Daily Active Users (DAU)  : {self.get_daily_active_users()}")
        session_info = self.get_session_metrics()
        print(f"Total Sessions            : {session_info['total_sessions']}")
        print(f"Unique Users              : {session_info['unique_users']}")
        print(f"Avg Sessions / User       : {session_info['avg_sessions_per_user']}")
        print(f"Avg Session Duration      : {self.get_average_session_duration()} seconds")
        print(f"Top Interactions          : {self.get_top_interactions()}")
        print(f"Bounce Rate               : {self.get_bounce_rate()}%")
        print(f"Conversion Rate           : {self.get_conversion_rate()}%")
        print(f"Device Usage Share (%)    : {self.get_device_share()}")
        print("=" * 50)

if __name__ == "__main__":
    engine = AnalyticsEngine("events.json")
    engine.run_self_verification()
    engine.generate_report()