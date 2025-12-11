# Navicat MySQL Connection Information

## Connection Details for Prontivus MySQL Database

Use these details to connect to your MySQL database using Navicat:

### General Tab

**Connection Name:**
```
Prontivus MySQL (Production)
```
*(You can use any name you prefer)*

**Host:**
```
db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com
```

**Port:**
```
3306
```

**User Name:**
```
admin
```

**Password:**
```
cMgoIYsgrGYlTt23LVVq
```

**Save password:** ✅ (Check this box to save the password)

### Databases Tab

**Default Database:**
```
prontivus_clinic
```

### Advanced Tab (Optional)

**Connection Timeout:** `30` seconds (default is fine)

**Keep-Alive Interval:** `30` seconds (default is fine)

### SSL Tab

**Use SSL:** ✅ **Check this** (AWS RDS requires SSL)

**SSL Mode:** `REQUIRED` or `PREFERRED`

**CA Certificate:** Leave empty (AWS RDS uses Amazon RDS CA)

### Connection String (URI)

If you need the full connection URI:
```
mysql://admin:cMgoIYsgrGYlTt23LVVq@db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com:3306/prontivus_clinic?ssl-mode=REQUIRED
```

## Steps to Connect

1. Open Navicat
2. Click "New Connection" → "MySQL"
3. Fill in the **General** tab with the information above
4. Go to **SSL** tab and enable SSL (REQUIRED for AWS RDS)
5. Click **Test Connection** to verify
6. If successful, click **OK** to save

## Important Notes

⚠️ **SSL is Required:** AWS RDS requires SSL connections. Make sure to enable SSL in the SSL tab.

⚠️ **Firewall:** Ensure your IP address is allowed in the AWS RDS security group if you're connecting from outside AWS.

⚠️ **Network Access:** The database is accessible from the internet, but you may need to whitelist your IP in AWS RDS security groups.

## Troubleshooting

**If connection fails:**

1. **Check SSL:** Make sure SSL is enabled in the SSL tab
2. **Check Firewall:** Verify your IP is allowed in AWS RDS security group
3. **Check Credentials:** Double-check username and password
4. **Check Host:** Verify the hostname is correct
5. **Check Port:** Ensure port 3306 is not blocked by your firewall

## Quick Reference

```
Host:     db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com
Port:     3306
User:     admin
Password: cMgoIYsgrGYlTt23LVVq
Database: prontivus_clinic
SSL:      REQUIRED
```

