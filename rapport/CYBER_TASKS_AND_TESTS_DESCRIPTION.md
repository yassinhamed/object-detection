# COMPREHENSIVE DESCRIPTION OF CYBER TASKS AND PERFORMANCE TESTS
## For AI Report Generation

---

## PART 1: MAIN CYBER TASKS

### Task 1: SERVER-SIDE ENCRYPTION (`server_encryption.py`)
**Module Name:** `ServerEncryption`

**Purpose:**
Encrypt video files on the sender side using military-grade AES-256-CBC encryption before transmission over the network.

**Cryptographic Algorithm:**
- **Algorithm:** AES (Advanced Encryption Standard)
- **Key Size:** 256 bits (AES-256)
- **Mode:** CBC (Cipher Block Chaining)
- **IV Size:** 128 bits (16 bytes) - randomly generated per file
- **Padding:** PKCS7 padding applied once to full plaintext

**Key Derivation:**
- **Function:** PBKDF2-HMAC-SHA256
- **Iterations:** 100,000 (strong protection against brute force)
- **Salt:** `"video_encryption_salt"` (fixed, can be customized)
- **Output:** 32 bytes (256-bit AES key)

**Key Methods:**
1. `encrypt_file(input_path, output_path)` - Encrypts full video file
   - Saves IV at beginning of output file
   - Adds `.enc` extension to output
   - Returns encrypted file path
2. `encrypt_file_stream(input_path)` - Returns encrypted bytes in memory for network transmission

**Processing:**
- Chunk-based streaming: 1MB per chunk (memory efficient for large video files)
- Each chunk padded before encryption if necessary

**Output Format:**
```
[16 bytes IV] + [Encrypted Data (PKCS7 padded)]
```

**Security Properties:**
- Prevents replay attacks (random IV per file)
- Prevents dictionary attacks (PBKDF2 key stretching)
- Provides semantic security (CBC mode)

---

### Task 2: CLIENT-SIDE DECRYPTION (`client_decryption.py`)
**Module Name:** `ClientDecryption`

**Purpose:**
Decrypt video files received from server using identical AES-256-CBC parameters as encryption.

**Cryptographic Parameters:**
- **Identical to Server Encryption** (same algorithm, key size, mode, salt, iterations)
- Ensures only clients with correct password can decrypt

**Key Methods:**
1. `decrypt_file(input_path, output_path)` - Decrypts `.enc` file
   - Reads IV from first 16 bytes
   - Decrypts remaining data
   - Removes PKCS7 padding
   - Saves decrypted file (removes `.enc` extension)
2. `decrypt_bytes_stream(encrypted_data)` - Decrypts data from network stream

**Padding Removal:**
- Validates PKCS7 padding before removal
- Checks that padding bytes are consistent
- Prevents padding oracle attacks

**Security Properties:**
- Lossless decryption (original file perfectly reconstructed)
- Symmetric encryption ensures reversibility
- Validation prevents corrupted decryption

---

### Task 3: VIDEO SERVER (`video_server.py`)
**Purpose:**
HTTP server for secure video storage, delivery, access control, and audit logging.

**Features:**
1. **Authentication:**
   - Cookie-based sessions (for web browsers)
   - HTTP Basic Authentication (for API clients)
   - Session timeout: 30 minutes (auto-extends with activity)
   - Credentials: admin / secure123 (default)

2. **HTTP Endpoints:**
   - `GET /` - Login page (HTML form)
   - `POST /login` - User authentication
   - `GET /api/videos` - List all encrypted videos (JSON)
   - `GET /download/{video_name}` - Download encrypted video file
   - `GET /stream/{video_name}` - Stream video (partial support)

3. **Access Control:**
   - Role-based authentication
   - Session-based authorization
   - IP tracking and logging

4. **Audit Logging (`server_access.log`):**
   - Records all user actions with timestamps
   - Logs: IP address, authenticated user, action, status
   - Format: `[YYYY-MM-DD HH:MM:SS] IP:{ip} | User:{username} | ACTION:{action} | STATUS:{status}`

5. **Network Discovery:**
   - UDP broadcast on port 9999
   - Allows clients to auto-discover server on LAN
   - Discovery message: `VIDEO_SERVER_DISCOVER`
   - Response: `VIDEO_SERVER_FOUND`

---

### Task 4: VIDEO CLIENT (`video_client.py`)
**Module Name:** `VideoClient`

**Purpose:**
Download encrypted videos from server with automatic LAN discovery and local decryption.

**Methods:**
1. `list_videos()` - Fetches list of available encrypted videos
   - Returns: Array of video metadata (name, size, modification date)
   - Authentication: HTTP Basic Auth

2. `download_video(video_name, output_path)` - Downloads and automatically decrypts
   - Shows progress bar (percentage + bytes downloaded)
   - Handles temporary file management
   - Calls `ClientDecryption` to decrypt after download
   - Cleans up temporary files on error

3. `discover_server()` - Auto-discovers video server on local network
   - Scans LAN for UDP response on port 9999
   - Timeout: 3 seconds per discovery attempt

**Workflow:**
```
1. Discover server on local network (UDP broadcast)
   ↓
2. Authenticate with credentials (admin/secure123)
   ↓
3. List available encrypted video files from /videos/ directory
   ↓
4. User selects video to download
   ↓
5. Download encrypted file in 1MB chunks (shows progress)
   ↓
6. Automatic decryption using ClientDecryption module
   ↓
7. Save decrypted file locally
```

---

### Task 5: YOLO OBJECT DETECTION (`yolo.py`)
**Purpose:**
Real-time object detection on video frames using YOLOv8-Nano neural network.

**Model:**
- **Architecture:** YOLOv8-Nano (lightweight, ~3.2M parameters)
- **Classes:** 80 object classes (persons, vehicles, animals, sports equipment, etc.)
- **Input Size:** 640×640 pixels
- **Device:** CPU or GPU (auto-selected)

**Methods:**
1. `detect(image, max_det=100)` - Detect objects in single frame
   - Returns: List of detections with boxes, scores, class IDs

2. `annotate(image, detections)` - Draw bounding boxes on image
   - Visualizes detected objects with labels and confidence scores

**Configuration:**
- **Confidence Threshold:** 0.25 (detection must be >25% confident)
- **IOU Threshold:** 0.45 (non-maximum suppression parameter)
- **Max Detections:** 100 objects per frame

**Output:** 
- Bounding boxes: `[x1, y1, x2, y2]` coordinates
- Confidence scores: 0.0-1.0
- Class labels: "person", "car", "dog", etc.

---

## PART 2: PERFORMANCE ANALYSIS TESTS

All tests are in directory: `performance_d'un_systeme_de_chiffrement/`

### TEST 1: ENCRYPTION TIME ANALYSIS
**File:** `encryption_time.py`
**Input:** Image file path
**Command:** `python encryption_time.py <image_file>`

**Purpose:**
Measure how fast AES-256-CBC encryption executes on image files.

**What It Measures:**
- Wall-clock execution time in seconds (6 decimal places precision)
- Time from start of encryption to file written to disk

**Process:**
1. Loads image file from disk
2. Derives AES key from password using PBKDF2
3. Generates random IV
4. Encrypts file using AES-256-CBC
5. Writes encrypted file (IV + ciphertext)
6. Records total execution time

**Output Format:**
```
==================================================
⏱️  Encryption Time Analysis
==================================================
File: <image_path>
Encrypted file: <output_path>
Execution time: <X.XXXX seconds>
==================================================
✅ Very fast encryption       (if < 1 second)
⚠️  Moderate speed            (if 1-3 seconds)
❌ Slow encryption            (if > 3 seconds)
==================================================
```

**Interpretation for Report:**
- **< 1 second:** Excellent (suitable for real-time applications)
- **1-3 seconds:** Acceptable for batch processing
- **> 3 seconds:** Bottleneck for large-scale deployment

**What To Report:**
- Execution time in seconds
- Performance category (fast/moderate/slow)
- File size encrypted
- Throughput calculation: `file_size / execution_time` (MB/s)

---

### TEST 2: DECRYPTION TIME ANALYSIS
**File:** `decryption_time.py`
**Input:** Encrypted file path (`.enc`)
**Command:** `python decryption_time.py <encrypted_file>`

**Purpose:**
Measure how fast AES-256-CBC decryption executes on encrypted files.

**What It Measures:**
- Decryption execution time (from reading encrypted file to plaintext output)
- Wall-clock time in seconds (6 decimal places)

**Process:**
1. Reads encrypted file (IV + ciphertext)
2. Extracts IV (first 16 bytes)
3. Derives AES key using PBKDF2 with same salt and password
4. Decrypts ciphertext using AES-256-CBC with extracted IV
5. Removes PKCS7 padding
6. Writes decrypted file to disk
7. Records total execution time

**Output Format:**
```
==================================================
⏱️  Decryption Time Analysis
==================================================
Input file: <encrypted_file>
Output file: <decrypted_file>
Execution time: <X.XXXXXX seconds>
==================================================
✅ Very fast decryption       (if < 1 second)
⚠️  Moderate speed            (if 1-3 seconds)
❌ Slow decryption            (if > 3 seconds)
==================================================
```

**Interpretation for Report:**
- **Should be similar to encryption time** (symmetric algorithm)
- Compare encryption time vs decryption time (should be roughly equal ±10%)
- Calculate decryption throughput: `file_size / execution_time`

**What To Report:**
- Decryption time in seconds
- Comparison with encryption time
- Throughput in MB/s
- Performance rating

---

### TEST 3: SHANNON ENTROPY ANALYSIS
**File:** `entropy_analyzer.py`
**Input:** Two files - original image and encrypted file
**Command:** `python entropy_analyzer.py <original_file> <encrypted_file>`

**Purpose:**
Verify that encryption produces truly random-looking output (no statistical patterns).

**What It Measures:**
Shannon Entropy in bits (0-8 for byte data)

**Formula:**
$$H(X) = -\sum_{i=0}^{255} P(x_i) \times \log_2(P(x_i))$$

Where:
- $P(x_i)$ = probability of byte value $i$ appearing in data
- $\log_2$ = logarithm base 2

**Process:**
1. Loads encrypted file and skips IV (first 16 bytes)
2. Counts frequency of each byte value (0-255)
3. Calculates probability distribution
4. Computes Shannon entropy using formula above

**Output Format:**
```
==================================================
SHANNON ENTROPY ANALYSIS
==================================================
Original file entropy: <X.XX bits>
Encrypted file entropy: <X.XX bits>
==================================================

Original Image:
- Entropy: ~4-6 bits (structured visual data)

Encrypted Data:
- Entropy: ~7.99-8.00 bits (random distribution)

Interpretation:
✅ Entropy > 7.95 bits = Excellent randomness
⚠️  Entropy 7.5-7.95 bits = Acceptable
❌ Entropy < 7.5 bits = Weak encryption (patterns detected)
```

**Interpretation for Report:**
- **8.0 bits:** Perfect randomness (all 256 byte values equally likely = 1/256 probability each)
- **7.99 bits:** Excellent (imperceptible deviation from perfect randomness)
- **< 7.5 bits:** Weak encryption (detectable statistical patterns = vulnerable to attack)

**Cryptographic Meaning:**
High entropy proves encryption destroys information structure and cannot be broken by frequency analysis or statistical attacks.

**What To Report:**
- Entropy value in bits
- Original vs encrypted comparison
- Interpretation (excellent/acceptable/weak)
- Percentage of max entropy achieved

---

### TEST 4: NPCR (Number of Pixel Change Rate)
**File:** `npcr_encrypted_bytes.py`
**Input:** Original image and encrypted file
**Command:** `python npcr_encrypted_bytes.py <image> <encrypted_file>`

**Purpose:**
Measure the **diffusion property** - how much output changes when input changes slightly.

**Formula:**
$$NPCR = \frac{\text{Number of different pixels}}{\text{Total pixels}} \times 100\%$$

**Process:**
1. Loads original image in grayscale
2. Loads encrypted file and skips IV
3. Truncates encrypted bytes to match image dimensions
4. Compares original image pixels vs encrypted bytes pixel-by-pixel
5. Counts how many differ
6. Calculates percentage

**Output Format:**
```
==================================================
NPCR (Number of Pixel Change Rate)
==================================================
Image: <image_path>
Encrypted file: <encrypted_path>
Image shape: <H x W>
Pixels compared: <number>

NPCR: <XX.XX%>
==================================================

Interpretation:
✅ NPCR > 99% = Excellent diffusion (avalanche effect)
⚠️  NPCR 80-99% = Acceptable diffusion
❌ NPCR < 50% = Weak diffusion (not recommended)
```

**Cryptographic Meaning:**
- **Diffusion:** One bit change in plaintext → multiple bits change in ciphertext
- **Avalanche Effect:** For strong encryption, changing 1 input bit should flip ~50% of output bits
- NPCR > 99% proves AES-256-CBC has strong diffusion

**What To Report:**
- NPCR percentage
- Number of pixels compared
- Interpretation (excellent/acceptable/weak)
- Confirmation that encryption meets NIST standards for diffusion

---

### TEST 5: UACI (Unified Average Changed Intensity) / Byte Variation Index
**File:** `uaci_calculator.py`
**Input:** Original image and encrypted file
**Command:** `python uaci_calculator.py <image> <encrypted_file>`

**Purpose:**
Measure **confusion property** - how much average byte values differ between plaintext and ciphertext.

**Formula (Byte Variation Index):**
$$BVI = \frac{\text{Mean Absolute Difference of Bytes}}{255} \times 100\%$$

Where absolute difference = $|pixel\_value - byte\_value|$

**Process:**
1. Loads original image in grayscale
2. Loads encrypted file (skips IV)
3. Truncates to same dimensions
4. Calculates absolute value difference for each pixel-byte pair
5. Averages all differences
6. Normalizes to percentage (max difference = 255)

**Output Format:**
```
==================================================
AES Encryption Analysis (Safe Metric)
==================================================
Image: <image_path>
Encrypted file: <encrypted_file>
Pixels compared: <number>

Byte Variation Index: <XX.XX%>
==================================================

Interpretation:
✅ BVI > 30% = High randomness (strong encryption)
⚠️  BVI 15-30% = Moderate randomness
❌ BVI < 15% = Weak encryption (predictable)
```

**Cryptographic Meaning:**
- **Confusion:** Output bytes cannot be simply derived from input bytes
- Measures how unpredictable the encryption is
- BVI > 30% proves strong confusion (resistant to cryptanalysis)

**Note:** Classical UACI is for image encryption. This version (Byte Variation Index) is adapted for AES because AES produces binary ciphertext, not spatial pixel structure.

**What To Report:**
- Byte Variation Index percentage
- Interpretation (high/moderate/weak)
- Comparison with theoretical random distribution (should be ~50%)

---

### TEST 6: CORRELATION ANALYSIS
**File:** `correlation_compare.py`
**Input:** Two images - original and decrypted
**Command:** `python correlation_compare.py <original_image> <decrypted_image>`

**Purpose:**
Verify that encryption-decryption process is **lossless** (no data corruption).

**Formula (Pearson Correlation Coefficient):**
$$r = \frac{\sum(x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum(x_i-\bar{x})^2}\sqrt{\sum(y_i-\bar{y})^2}}$$

Where:
- $x_i$ = pixel values in original image
- $y_i$ = pixel values in decrypted image
- Range: -1 to +1

**Process:**
1. Loads original image in grayscale
2. Loads decrypted image in grayscale
3. Flattens both to 1D arrays
4. Calculates Pearson correlation coefficient

**Output Format:**
```
==================================================
CORRELATION COMPARISON
==================================================
Image 1: <original_image_path>
Image 2: <decrypted_image_path>

Correlation: <X.XXXXXX>
==================================================

Interpretation:
✅ r = 1.0 = Perfect match (encryption perfectly reversible)
✅ r > 0.99 = Excellent (negligible corruption)
⚠️  r 0.95-0.99 = Acceptable (minor data loss)
❌ r < 0.95 = Decryption error (data corruption)
```

**Interpretation for Report:**
- **r = 1.0:** Byte-for-byte identical (perfect encryption/decryption)
- **r > 0.99:** Practically identical (suitable for real-world use)
- **r < 0.95:** Unacceptable (indicates bugs in encryption/decryption)

**Data Integrity Verification:**
This test proves that the encryption system is lossless and fully reversible, ensuring no information loss during encryption/decryption cycles.

**What To Report:**
- Correlation coefficient value
- Interpretation (perfect/excellent/acceptable/error)
- Confirmation of data integrity

---

### TEST 7: HISTOGRAM ANALYSIS
**File:** `histogram.py`
**Input:** Original image and encrypted file
**Command:** `python histogram.py <image> <encrypted_file>`

**Purpose:**
Visualize and compare byte distributions to confirm encryption removes statistical patterns.

**What It Measures:**
Frequency distribution of pixel/byte values (0-255)

**Process:**
1. Loads original image in grayscale
2. Loads encrypted file (skips IV)
3. Generates two histograms:
   - **Histogram 1:** Original image byte distribution (blue)
   - **Histogram 2:** Encrypted data byte distribution (red)
4. Displays side-by-side comparison using matplotlib

**Visual Interpretation:**

**Original Image Histogram:**
- **Shape:** Non-uniform distribution (peaks and valleys)
- **Meaning:** Visual content creates certain byte frequencies
- **Example:** Dark areas → more low values (0-50), bright areas → high values (200-255)

**Encrypted Data Histogram:**
- **Shape:** Flat/uniform distribution (all bars roughly equal height)
- **Meaning:** All 256 byte values equally likely
- **Security:** Hides all information about original image

**Output Analysis:**
```
✔ Original: structured distribution (image content)
✔ Encrypted: uniform distribution (randomness)
✔ Good encryption → flat histogram
```

**Report Sections:**
- Visual comparison of histograms
- Original histogram shape description
- Encrypted histogram shape description
- Uniformity metric (standard deviation of bar heights)
- Conclusion: Information destruction verified

---

### TEST 8: IMAGE ENCRYPTION/DECRYPTION
**Files:** `image_encryption.py`, `image_decryption.py`
**Command (Encrypt):** `python image_encryption.py <image_path>`
**Command (Decrypt):** `python image_decryption.py <encrypted_file.enc>`

**Purpose:**
Core encryption/decryption functionality for image files (building blocks for video encryption).

**ImageEncryption Class:**
- **Key Method:** `encrypt_file(input_path, output_path)`
- **Input:** Image file (PNG, JPG, etc.)
- **Output:** `<filename>.enc` (IV + encrypted data)
- **Process:**
  1. Read image file completely
  2. Derive AES key: `PBKDF2-HMAC-SHA256(password, salt, 100000 iterations, 32 bytes)`
  3. Generate random IV (16 bytes)
  4. Apply PKCS7 padding (pad to multiple of 16 bytes)
  5. Encrypt padded data with AES-256-CBC
  6. Write: [IV (16 bytes)] + [Ciphertext]

**ImageDecryption Class:**
- **Key Method:** `decrypt_file(input_path, output_path)`
- **Input:** Encrypted file (`.enc`)
- **Output:** `<filename>_decrypted.jpg`
- **Process:**
  1. Read encrypted file
  2. Extract IV (first 16 bytes)
  3. Derive same AES key with same password
  4. Decrypt ciphertext with AES-256-CBC
  5. Remove PKCS7 padding
  6. Write decrypted image

**File Format:**
```
[16 bytes: IV] + [N bytes: AES-256-CBC(PKCS7(plaintext))]
```

**PKCS7 Padding:**
- Adds N bytes to end of data, each byte = N
- N = 16 - (len(data) % 16)
- Example: If data is 10 bytes → add 6 bytes each with value 6
- Allows decryption to verify proper padding

---

## PART 3: HOW TO USE THIS DESCRIPTION FOR REPORT GENERATION

### Step 1: Run Each Test and Collect Output
Execute each test script and save the console output:

```bash
# Encryption Performance
python encryption_time.py performance_d'un_systeme_de_chiffrement/mr_robot.jpg
# Save output → ENCRYPTION_TIME_OUTPUT.txt

# Decryption Performance
python decryption_time.py performance_d'un_systeme_de_chiffrement/mr_robot.jpg.enc
# Save output → DECRYPTION_TIME_OUTPUT.txt

# Entropy Analysis
python entropy_analyzer.py performance_d'un_systeme_de_chiffrement/mr_robot.jpg performance_d'un_systeme_de_chiffrement/mr_robot.jpg.enc
# Save output → ENTROPY_OUTPUT.txt

# NPCR Analysis
python npcr_encrypted_bytes.py performance_d'un_systeme_de_chiffrement/mr_robot.jpg performance_d'un_systeme_de_chiffrement/mr_robot.jpg.enc
# Save output → NPCR_OUTPUT.txt

# UACI Analysis
python uaci_calculator.py performance_d'un_systeme_de_chiffrement/mr_robot.jpg performance_d'un_systeme_de_chiffrement/mr_robot.jpg.enc
# Save output → UACI_OUTPUT.txt

# Correlation Analysis
python correlation_compare.py performance_d'un_systeme_de_chiffrement/mr_robot.jpg performance_d'un_systeme_de_chiffrement/mr_robot.jpg_decrypted.jpg
# Save output → CORRELATION_OUTPUT.txt

# Histogram Analysis
python histogram.py performance_d'un_systeme_de_chiffrement/mr_robot.jpg performance_d'un_systeme_de_chiffrement/mr_robot.jpg.enc
# Save output + screenshot → HISTOGRAM_OUTPUT.txt + HISTOGRAM_SCREENSHOT.png
```

### Step 2: Extract Key Metrics
From each output, extract:

**Encryption Time:**
- Execution time (seconds)
- File size (bytes)
- Calculate throughput: `size / time` (MB/s)

**Decryption Time:**
- Execution time (seconds)
- Compare to encryption time (should be ±10% similar)
- Calculate throughput

**Entropy:**
- Original entropy (bits)
- Encrypted entropy (bits)
- Difference from perfect 8.0 bits

**NPCR:**
- Percentage value
- Interpretation: excellent/acceptable/weak

**UACI (BVI):**
- Percentage value
- Interpretation: high/moderate/weak

**Correlation:**
- Correlation coefficient
- Data integrity status

**Histogram:**
- Original histogram shape (described)
- Encrypted histogram shape (uniform)
- Visual confirmation of information destruction

### Step 3: Structure Report Sections

**1. Executive Summary**
- Project goal (secure video streaming with encryption)
- Key technologies (AES-256-CBC, YOLOv8, HTTP server)

**2. Cryptographic Algorithm Analysis**
- AES-256-CBC specifications
- Key derivation method
- Padding scheme
- Security advantages

**3. Performance Analysis**
- Encryption/Decryption speed benchmarks
- Throughput calculations
- Real-time applicability assessment

**4. Security Analysis**
- Entropy verification (randomness)
- Diffusion property (NPCR)
- Confusion property (UACI)
- Data integrity (correlation)
- Pattern elimination (histogram)

**5. Conclusions**
- System security strength confirmed
- Performance suitable for deployment
- Recommendations for production use

---

## PART 4: EXPECTED OUTPUT EXAMPLES

### Example: Entropy Analyzer Output
```
==================================================
SHANNON ENTROPY ANALYSIS
==================================================
File 1: mr_robot.jpg
File 2: mr_robot.jpg.enc

Original File:
  Entropy: 5.42 bits
  Interpretation: Typical image data

Encrypted File:
  Entropy: 7.998 bits
  Interpretation: Near-perfect randomness

Difference: 2.578 bits
Status: ✅ Excellent encryption (entropy increase = entropy loss of plaintext)
==================================================
```

### Example: NPCR Output
```
==================================================
NPCR (Number of Pixel Change Rate)
==================================================
Image: mr_robot.jpg
Encrypted file: mr_robot.jpg.enc
Image shape: (564, 564)
Pixels compared: 318096

NPCR: 99.95%
==================================================
Interpretation:
✅ NPCR > 99% = Excellent diffusion (avalanche effect)

This value confirms that AES-256-CBC encryption produces
strong diffusion properties, meeting NIST encryption standards.
```

### Example: Correlation Output
```
==================================================
CORRELATION COMPARISON
==================================================
Image 1: mr_robot.jpg
Image 2: mr_robot.jpg_decrypted.jpg

Correlation: 1.000000
==================================================
Interpretation:
✔ Images are almost identical (correct decryption)

Perfect correlation (r = 1.0) proves:
- Encryption process is 100% reversible
- No data loss or corruption
- Decryption algorithm correctly implemented
```

---

**END OF DESCRIPTION**

This document provides all information needed for an AI system to write a comprehensive technical report about your project's encryption system, performance, and security properties.
