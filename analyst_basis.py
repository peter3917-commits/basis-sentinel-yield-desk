import pandas as pd

class AnalystBasis:
    def __init__(self, data_frame):
        """
        Purpose: Analyze the scouted data to find yield opportunities.
        """
        self.df = data_frame

    def get_yield_heatmap(self):
        """Calculates the Projected APY for the six-coin basket."""
        if self.df.empty:
            return "⚠️ No data available for analysis."

        # Get the latest entry for each asset
        latest_data = self.df.sort_values('timestamp').groupby('asset').last().reset_index()
        
        # Annualize the funding rate: (Rate * 3 payouts/day * 365 days) * 100
        latest_data['projected_apy'] = latest_data['funding_rate'].apply(lambda x: round(x * 3 * 365 * 100, 2))
        
        # Sort by best yield
        heatmap = latest_data[['asset', 'projected_apy', 'funding_rate', 'basis_gap']].sort_values('projected_apy', ascending=False)
        
        return heatmap

    def check_for_negative_funding(self):
        """Alerts if we are currently paying to keep a position open."""
        negatives = self.df[self.df['funding_rate'] < 0]
        return negatives if not negatives.empty else None
