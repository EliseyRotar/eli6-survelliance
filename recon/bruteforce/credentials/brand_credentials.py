"""Brand-specific credential DB expanded from CamXploit.

Format: { 'brand_or_family': [(user, password), ...] }
Source: CamXploit v2.0.2 (spyboy-productions) plus our existing 327-line DB.
"""

# HIKVISION
HIKVISION = [
    ('admin', '12345'),
    ('admin', 'admin'),
    ('admin', '888888'),
    ('admin', '666666'),
    ('admin', 'hikvision'),
    ('admin', 'hk12345'),
    ('admin', 'hk12345.'),
    ('admin', 'hik12345'),
    ('admin', 'hik12345.'),
    ('admin', 'pass'),
    ('admin', 'password'),
    ('admin', '1234'),
    ('admin', 'admin123'),
    ('admin', 'Admin123'),
    ('admin', 'abcd1234'),
    ('admin', 'a123456'),
    ('admin', '12345678'),
    ('admin', '1111'),
    ('admin', '0000'),
    ('admin', '9999'),
    ('admin', '4321'),
    ('admin', 'admin@1234'),
    ('admin', 'sysadmin'),
]

# DAHUA
DAHUA = [
    ('admin', 'admin'),
    ('admin', 'dahua'),
    ('admin', '1234'),
    ('admin', 'admin123'),
    ('admin', 'Admin123'),
    ('admin', '888888'),
    ('admin', '666666'),
    ('admin', 'password'),
    ('admin', 'pass'),
    ('admin', '7ujM8'),  # Dahua known root
    ('admin', '12345'),
    ('admin', '7ujM8C'),
    ('admin', 'dvr'),
    ('admin', 'nvr'),
    ('admin', 'dvr123'),
    ('admin', 'dh1234'),
    ('admin', 'dh12345'),
]

# AXIS
AXIS = [
    ('root', 'pass'),
    ('root', 'root'),
    ('root', ''),
    ('admin', ''),
    ('admin', 'admin'),
    ('admin', '1234'),
    ('admin', 'password'),
    ('admin', 'pass'),
]

# CP Plus
CP_PLUS = [
    ('admin', 'admin'),
    ('admin', '1234'),
    ('admin', '888888'),
    ('admin', 'password'),
    ('admin', 'admin123'),
    ('admin', 'Admin123'),
    ('admin', 'CP12345'),
    ('admin', 'cp1234'),
    ('admin', 'cplus123'),
    ('admin', 'uvr123'),
]

# HI3510 / HiSilicon / Hipcam
HIPCAM = [
    ('admin', 'admin'),
    ('admin', '12345'),
    ('admin', 'hipcam'),
    ('admin', 'hislib'),
    ('admin', ''),
    ('admin', '1234'),
    ('admin', '888888'),
    ('admin', 'admin123'),
    ('admin', 'XVR12345'),  # Xiongmai OEM
]

# GENERIC NVR/DVR user-specific defaults
GENERIC_NVR = [
    ('user', 'user'),
    ('user', '1234'),
    ('user', '12345'),
    ('operator', 'operator'),
    ('supervisor', 'supervisor'),
    ('support', 'support'),
    ('system', 'system'),
    ('viewer', 'viewer'),
    ('guest', 'guest'),
    ('administrator', 'administrator'),
    ('admin1', 'admin'),
    ('admin1', 'password'),
]

PRIORITY_BRUTEFORCE = [
    # Hikvision
    ('admin', '12345'),
    ('admin', 'admin'),
    ('admin', '888888'),
    ('admin', 'hikvision'),
    # Dahua
    ('admin', 'admin'),
    ('admin', 'dahua'),
    # Axis
    ('root', 'pass'),
    # Hipcam / HiSilicon / Xiongmai
    ('admin', 'admin'),
    ('admin', 'hipcam'),
    # CP Plus
    ('admin', 'admin'),
    ('admin', 'cp1234'),
    # Try empty
    ('admin', ''),
]
