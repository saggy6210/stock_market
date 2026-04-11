#!/usr/bin/env python3
"""
CLI script to manually generate dashboard data.

Usage:
    python generate_dashboard.py [--output-dir /path/to/output]

This script triggers the dashboard data pipeline which:
1. Fetches real-time index prices (NIFTY, SENSEX, etc.)
2. Fetches commodity prices (Gold, Silver, Crude, etc.)
3. Generates screener data (stocks fallen from 52-week highs)
4. Fetches FII/DII activity data
5. Generates market outlook
6. Generates stock movement predictions
7. Saves all data to JSON for the dashboard

The same pipeline is also run automatically via:
- Scheduler: 6:55 AM (pre-market) and 3:35 PM (post-market) IST
- API: POST /api/generate-dashboard-data
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.analysis.dashboard_pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Generate dashboard data for the market analysis dashboard"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for generated files (default: market_dashboard/data)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("📊 Market Dashboard Data Pipeline")
    print("=" * 60)
    
    try:
        print("\n🔄 Running pipeline...")
        data = run_pipeline(args.output_dir)
        
        print("\n✅ Pipeline completed successfully!")
        print("\n📈 Generated Data Summary:")
        print(f"   - Timestamp: {data.get('timestamp')}")
        print(f"   - Indices: {len(data.get('indices', {}))} items")
        print(f"   - Commodities: {len(data.get('commodities', {}))} items")
        
        screener = data.get('screener', {})
        for period, stocks in screener.items():
            print(f"   - Screener ({period}): {len(stocks)} stocks")
        
        print(f"   - Predictions: {len(data.get('predictions', []))} items")
        
        output_dir = args.output_dir or str(Path(__file__).parent / "market_dashboard" / "data")
        print(f"\n📁 Output files saved to: {output_dir}")
        print(f"   - dashboard_data.json")
        print(f"   - dashboard_data.js")
        
        print("\n" + "=" * 60)
        print("✨ Dashboard data is ready!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
