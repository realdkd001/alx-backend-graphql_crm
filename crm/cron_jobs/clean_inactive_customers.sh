
#!/bin/bash
# Script to delete inactive customers (no orders in the last year)

# Log file
LOG_FILE="/tmp/customer_cleanup_log.txt"

# Run Django shell command to delete inactive customers
DELETED_COUNT=$(python manage.py shell -c "
from django.utils import timezone
from datetime import timedelta
from crm.models import Customer

cutoff_date = timezone.now() - timedelta(days=365)
inactive_customers = Customer.objects.filter(
    orders__isnull=True
) | Customer.objects.filter(
    orders__created_at__lt=cutoff_date
).distinct()

count = inactive_customers.count()
inactive_customers.delete()
print(count)
")

# Append result with timestamp to log
echo \"\$(date '+%Y-%m-%d %H:%M:%S') - Deleted \$DELETED_COUNT inactive customers\" >> \$LOG_FILE