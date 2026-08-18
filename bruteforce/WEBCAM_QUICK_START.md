# 🎥 IoT Webcam Brute Force - Quick Start Guide

## ⚠️ IMPORTANT: Use ONLY on your own devices!

## 🚀 FASTEST WAY - For Your IoT Webcam

### **Use This Tool:** `iot_webcam_bruteforce.py`

This is the **simplest and fastest** tool specifically designed for IoT webcams.

### Quick Usage:

```bash
cd bruteforce

# If your webcam is at 192.168.1.100
./iot_webcam_bruteforce.py 192.168.1.100

# Or with full URL
./iot_webcam_bruteforce.py http://192.168.1.100

# Slower testing (more respectful)
./iot_webcam_bruteforce.py 192.168.1.100 -d 2.0
```

### What it does:

- ✅ Tests 35+ most common IoT webcam credentials
- ✅ Ordered by likelihood (tests most common first)
- ✅ Fast and efficient
- ✅ Shows results immediately when found
- ✅ Simple to use

---

## 🎯 Alternative Tools (More Advanced)

### 1. **camera_bruteforce.py** - Full camera testing

More comprehensive, tests 80+ credentials:

```bash
./camera_bruteforce.py http://192.168.1.100
```

### 2. **brand_specific_bruteforce.py** - If you know the brand

If you know your webcam brand (e.g., HIKVision, Dahua):

```bash
# List supported brands
./brand_specific_bruteforce.py --list-brands

# Test specific brand
./brand_specific_bruteforce.py 192.168.1.100 -b hikvision
```

---

## 📊 Comparison Table

| Tool                         | Best For        | Speed        | Credentials    | Difficulty  |
| ---------------------------- | --------------- | ------------ | -------------- | ----------- |
| **iot_webcam_bruteforce.py** | Your IoT webcam | ⚡ Fast      | 35+            | ⭐ Easy     |
| camera_bruteforce.py         | Any IP camera   | 🐢 Slower    | 80+            | ⭐⭐ Medium |
| brand_specific_bruteforce.py | Known brands    | ⚡⚡ Fastest | Brand-specific | ⭐⭐ Medium |

---

## 🎯 RECOMMENDED FOR YOU

Since you want to brute force your IoT webcam, use:

```bash
cd bruteforce
./iot_webcam_bruteforce.py YOUR_WEBCAM_IP
```

**Example:**

```bash
./iot_webcam_bruteforce.py 192.168.1.100
```

This will:

1. Test the most common IoT webcam credentials
2. Show you working credentials immediately
3. Complete in 1-2 minutes
4. Give you the username/password to access your webcam

---

## 💡 Common IoT Webcam IPs

Your webcam is likely at one of these IPs:

- `192.168.1.100` - `192.168.1.254`
- `192.168.0.100` - `192.168.0.254`
- `10.0.0.100` - `10.0.0.254`

To find your webcam IP:

```bash
# Scan your network
nmap -sn 192.168.1.0/24

# Or check your router's connected devices
```

---

## 🔐 Most Common IoT Webcam Credentials

The tool tests these in order:

1. admin:admin
2. admin:123456
3. admin:(empty)
4. admin:password
5. admin:1234
6. root:pass
7. root:(empty)
8. And 28 more...

---

## ✅ Success Example

```
🎥 Testing IoT Webcam: http://192.168.1.100
📊 Testing 35 common credential combinations
============================================================
[ 1/35] Testing admin:admin ... ❌ Unauthorized
[ 2/35] Testing admin:123456 ... ✅ SUCCESS!
🎯 WORKING CREDENTIALS FOUND: admin:123456

============================================================
🎯 RESULTS
============================================================
✅ SUCCESSFUL CREDENTIALS FOUND:
   👤 admin:123456

🌐 Access your webcam at: http://192.168.1.100
💡 Try these credentials in your browser or webcam software
```

---

## 🛠️ Troubleshooting

**"Connection Error"**

- Check if the IP is correct
- Make sure webcam is powered on
- Verify you're on the same network

**"No working credentials found"**

- Default credentials may have been changed
- Try the full camera_bruteforce.py tool
- Check webcam manual for default credentials

**"Timeout"**

- Webcam might be slow, increase delay: `-d 3.0`
- Check network connection

---

## 📝 After Finding Credentials

Once you find the credentials:

1. **Access via browser:** `http://YOUR_WEBCAM_IP`
2. **Login** with the found username/password
3. **Change the default password** for security!
4. **Configure** your webcam settings

---

## 🎉 You're Ready!

Just run:

```bash
cd bruteforce
./iot_webcam_bruteforce.py YOUR_WEBCAM_IP
```

Good luck! 🚀
