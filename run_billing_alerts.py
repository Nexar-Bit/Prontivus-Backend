"""
Script to run billing alerts manually
Can be scheduled as a cron job or run manually

Usage:
    python run_billing_alerts.py [--overdue] [--upcoming] [--all]
    
Examples:
    python run_billing_alerts.py --all          # Check both overdue and upcoming
    python run_billing_alerts.py --overdue      # Check only overdue invoices
    python run_billing_alerts.py --upcoming     # Check only upcoming due dates
"""
import asyncio
import argparse
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from database import get_async_session
from app.models import Clinic
from app.services.billing_alert_service import billing_alert_service
from sqlalchemy import select


async def run_alerts(check_overdue: bool = True, check_upcoming: bool = True):
    """Run billing alerts for all clinics"""
    print("=" * 60, flush=True)
    print("🚀 Starting Billing Alerts Check", flush=True)
    print("=" * 60, flush=True)
    
    async for db in get_async_session():
        try:
            # Get all active clinics
            clinics_query = select(Clinic).filter(Clinic.is_active == True)
            result = await db.execute(clinics_query)
            clinics = result.scalars().all()
            
            if not clinics:
                print("⚠️  No active clinics found")
                return
            
            print(f"\n📋 Found {len(clinics)} active clinic(s)\n")
            
            total_overdue = 0
            total_upcoming = 0
            
            for clinic in clinics:
                print(f"🏥 Processing clinic: {clinic.name} (ID: {clinic.id})")
                print("-" * 60)
                
                if check_overdue:
                    print("  🔍 Checking overdue invoices...")
                    overdue_alerts = await billing_alert_service.check_overdue_invoices(
                        clinic_id=clinic.id,
                        db=db,
                        send_notifications=True
                    )
                    total_overdue += len(overdue_alerts)
                    if overdue_alerts:
                        print(f"  ⚠️  Found {len(overdue_alerts)} overdue invoice(s)")
                        for alert in overdue_alerts:
                            print(f"     - Invoice #{alert['invoice_id']}: {alert['patient_name']} - R$ {alert['outstanding_amount']:,.2f} ({alert['days_overdue']} days overdue)")
                    else:
                        print("  ✅ No overdue invoices")
                
                if check_upcoming:
                    print("  🔍 Checking upcoming due dates...")
                    upcoming_alerts = await billing_alert_service.check_upcoming_due_dates(
                        clinic_id=clinic.id,
                        db=db,
                        send_notifications=True
                    )
                    total_upcoming += len(upcoming_alerts)
                    if upcoming_alerts:
                        print(f"  📅 Found {len(upcoming_alerts)} invoice(s) with upcoming due dates")
                        for alert in upcoming_alerts:
                            print(f"     - Invoice #{alert['invoice_id']}: {alert['patient_name']} - R$ {alert['outstanding_amount']:,.2f} (due in {alert['days_until_due']} days)")
                    else:
                        print("  ✅ No upcoming due dates")
                
                print()
            
            print("=" * 60)
            print("📊 Summary:")
            print(f"   Overdue invoices: {total_overdue}")
            print(f"   Upcoming due dates: {total_upcoming}")
            print("=" * 60)
            print("✅ Billing alerts check completed!")
            
        except Exception as e:
            print(f"\n❌ Error running billing alerts: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            break  # Exit after first iteration (single session)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run billing alerts for all clinics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_billing_alerts.py --all          # Check both overdue and upcoming
  python run_billing_alerts.py --overdue      # Check only overdue invoices
  python run_billing_alerts.py --upcoming     # Check only upcoming due dates
        """
    )
    
    parser.add_argument(
        "--overdue",
        action="store_true",
        help="Check and send alerts for overdue invoices"
    )
    parser.add_argument(
        "--upcoming",
        action="store_true",
        help="Check and send alerts for upcoming due dates"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check both overdue and upcoming (default if no flags specified)"
    )
    
    args = parser.parse_args()
    
    # Determine what to check
    check_overdue = args.overdue or args.all or (not args.overdue and not args.upcoming)
    check_upcoming = args.upcoming or args.all or (not args.overdue and not args.upcoming)
    
    if not check_overdue and not check_upcoming:
        print("⚠️  No checks specified. Use --overdue, --upcoming, or --all")
        return
    
    # Run async function
    asyncio.run(run_alerts(check_overdue=check_overdue, check_upcoming=check_upcoming))


if __name__ == "__main__":
    main()
