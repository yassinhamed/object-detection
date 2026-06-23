#!/usr/bin/env python3
"""
Entropy and Randomness Analyzer
Measures Shannon entropy of encrypted data to verify true randomness.
High entropy confirms proper encryption.
"""

import numpy as np
from pathlib import Path
import sys
from collections import Counter


def load_encrypted_file(encrypted_file_path: str) -> np.ndarray:
    """
    Load encrypted file and skip the IV header.
    
    Args:
        encrypted_file_path: Path to encrypted file
        
    Returns:
        Encrypted bytes (without IV)
    """
    if not Path(encrypted_file_path).exists():
        raise FileNotFoundError(f"File not found: {encrypted_file_path}")
    
    IV_SIZE = 16
    
    with open(encrypted_file_path, 'rb') as f:
        # Skip IV
        f.read(IV_SIZE)
        # Read encrypted data
        encrypted_bytes = f.read()
    
    return np.frombuffer(encrypted_bytes, dtype=np.uint8)


def load_file_as_bytes(file_path: str) -> np.ndarray:
    """Load file as raw bytes."""
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'rb') as f:
        data = f.read()
    
    return np.frombuffer(data, dtype=np.uint8)


def calculate_shannon_entropy(data: np.ndarray) -> float:
    """
    Calculate Shannon entropy of data.
    
    Shannon Entropy Formula:
        H(X) = -Σ P(x) * log2(P(x))
    
    Where:
        - P(x) = probability of byte value x
        - log2 = logarithm base 2
    
    Perfect entropy (random):
        - H = 8 bits (for byte values 0-255)
        - All 256 values equally likely
    
    Low entropy (non-random):
        - H < 8 bits
        - Some values more likely than others
    
    Args:
        data: Array of byte values
        
    Returns:
        Entropy in bits (0-8 for byte data)
    """
    # Count frequency of each byte value
    byte_counts = np.bincount(data, minlength=256)
    
    # Calculate probabilities
    probabilities = byte_counts / len(data)
    
    # Remove zero probabilities (log of zero is undefined)
    probabilities = probabilities[probabilities > 0]
    
    # Calculate Shannon entropy: -Σ P(x) * log2(P(x))
    entropy = -np.sum(probabilities * np.log2(probabilities))
    
    return entropy


def calculate_chi_square_test(data: np.ndarray) -> tuple:
    """
    Perform chi-square test for randomness.
    
    Tests if all 256 byte values occur with equal frequency.
    
    Chi-Square Formula:
        χ² = Σ ((observed - expected)² / expected)
    
    For random data with n bytes:
        - Expected frequency = n / 256
        - χ² should be around 256 (±σ)
    
    Args:
        data: Array of byte values
        
    Returns:
        (chi_square_statistic, p_value_interpretation)
    """
    # Count frequency of each byte value
    byte_counts = np.bincount(data, minlength=256)
    
    # Expected frequency for each byte value (uniform distribution)
    expected_frequency = len(data) / 256
    
    # Calculate chi-square statistic
    chi_square = np.sum(((byte_counts - expected_frequency) ** 2) / expected_frequency)
    
    # Degrees of freedom = 255 (256 categories - 1)
    # Expected value for chi-square ≈ 255
    # Interpretation: if chi_square ≈ 255, data is likely random
    
    return chi_square, expected_frequency * 256


def analyze_byte_distribution(data: np.ndarray) -> dict:
    """
    Analyze distribution of byte values.
    
    Args:
        data: Array of byte values
        
    Returns:
        Dictionary with distribution statistics
    """
    byte_counts = np.bincount(data, minlength=256)
    
    # Calculate statistics
    mean_count = np.mean(byte_counts)
    std_count = np.std(byte_counts)
    min_count = np.min(byte_counts)
    max_count = np.max(byte_counts)
    
    # Count how many byte values appeared
    unique_bytes = np.count_nonzero(byte_counts)
    
    return {
        "mean_count": mean_count,
        "std_count": std_count,
        "min_count": min_count,
        "max_count": max_count,
        "unique_bytes": unique_bytes,
        "missing_bytes": 256 - unique_bytes
    }


def analyze_file(file_path: str, is_encrypted: bool = True) -> dict:
    """
    Analyze randomness of a file.
    
    Args:
        file_path: Path to file
        is_encrypted: Whether to skip IV header
        
    Returns:
        Dictionary with analysis results
    """
    print(f"📁 Loading file: {file_path}")
    
    if is_encrypted:
        data = load_encrypted_file(file_path)
        print(f"   Loaded {len(data):,} bytes (IV skipped)")
    else:
        data = load_file_as_bytes(file_path)
        print(f"   Loaded {len(data):,} bytes")
    
    print(f"\n🔍 Calculating entropy...")
    entropy = calculate_shannon_entropy(data)
    
    print(f"📊 Analyzing byte distribution...")
    dist_stats = analyze_byte_distribution(data)
    
    print(f"📈 Performing chi-square test...")
    chi_square, expected_chi = calculate_chi_square_test(data)
    
    results = {
        "file_path": file_path,
        "file_size": len(data),
        "entropy": entropy,
        "distribution": dist_stats,
        "chi_square": chi_square,
        "expected_chi_square": expected_chi
    }
    
    return results


def print_results(original_results: dict, encrypted_results: dict) -> None:
    """Print analysis results."""
    
    print(f"\n{'='*70}")
    print(f"Entropy and Randomness Analysis")
    print(f"{'='*70}\n")
    
    # Original file
    print(f"📄 Original File: {original_results['file_path']}")
    print(f"{'-'*70}")
    print(f"File Size: {original_results['file_size']:,} bytes")
    print(f"Shannon Entropy: {original_results['entropy']:.6f} bits")
    print(f"  (Max possible: 8 bits for random data)")
    print(f"\nByte Distribution:")
    print(f"  Mean frequency: {original_results['distribution']['mean_count']:.2f}")
    print(f"  Std deviation: {original_results['distribution']['std_count']:.2f}")
    print(f"  Min frequency: {original_results['distribution']['min_count']}")
    print(f"  Max frequency: {original_results['distribution']['max_count']}")
    print(f"  Unique bytes: {original_results['distribution']['unique_bytes']}/256")
    print(f"  Missing bytes: {original_results['distribution']['missing_bytes']}")
    print(f"\nChi-Square Test:")
    print(f"  χ² = {original_results['chi_square']:.2f}")
    print(f"  Expected: ~256 ± ~16")
    
    # Encrypted file
    print(f"\n🔐 Encrypted File: {encrypted_results['file_path']}")
    print(f"{'-'*70}")
    print(f"File Size: {encrypted_results['file_size']:,} bytes")
    print(f"Shannon Entropy: {encrypted_results['entropy']:.6f} bits")
    print(f"  (Max possible: 8 bits for random data)")
    print(f"\nByte Distribution:")
    print(f"  Mean frequency: {encrypted_results['distribution']['mean_count']:.2f}")
    print(f"  Std deviation: {encrypted_results['distribution']['std_count']:.2f}")
    print(f"  Min frequency: {encrypted_results['distribution']['min_count']}")
    print(f"  Max frequency: {encrypted_results['distribution']['max_count']}")
    print(f"  Unique bytes: {encrypted_results['distribution']['unique_bytes']}/256")
    print(f"  Missing bytes: {encrypted_results['distribution']['missing_bytes']}")
    print(f"\nChi-Square Test:")
    print(f"  χ² = {encrypted_results['chi_square']:.2f}")
    print(f"  Expected: ~256 ± ~16")
    
    # Assessment
    print(f"\n{'='*70}")
    print(f"Encryption Quality Assessment")
    print(f"{'='*70}")
    
    entropy_diff = encrypted_results['entropy'] - original_results['entropy']
    print(f"Entropy Increase: {entropy_diff:.6f} bits")
    
    if encrypted_results['entropy'] > 7.9:
        entropy_verdict = "✅ Excellent - Very close to theoretical maximum"
    elif encrypted_results['entropy'] > 7.5:
        entropy_verdict = "✅ Very Good - Strong randomness"
    elif encrypted_results['entropy'] > 7.0:
        entropy_verdict = "✅ Good - Acceptable randomness"
    else:
        entropy_verdict = "❌ Poor - Insufficient randomness"
    
    print(f"Entropy Verdict: {entropy_verdict}")
    
    # Chi-square assessment
    chi_diff = abs(encrypted_results['chi_square'] - 256)
    if chi_diff < 50:
        chi_verdict = "✅ Pass - Uniform byte distribution"
    elif chi_diff < 100:
        chi_verdict = "✅ Acceptable - Reasonably uniform"
    else:
        chi_verdict = "❌ Fail - Non-uniform distribution"
    
    print(f"Chi-Square Verdict: {chi_verdict}")
    
    print(f"\n{'='*70}")
    print(f"CONCLUSION: ", end="")
    if encrypted_results['entropy'] > 7.9 and chi_diff < 50:
        print("✅ AES-CBC IS WORKING PROPERLY")
        print("The encrypted data is truly random with proper byte distribution.")
    elif encrypted_results['entropy'] > 7.5:
        print("✅ AES-CBC IS WORKING (minor variations expected)")
        print("Randomness is very good, small deviations are normal.")
    else:
        print("❌ AES-CBC MAY HAVE ISSUES")
        print("Encrypted data doesn't show expected randomness properties.")
    print(f"{'='*70}\n")


def main():
    """Main function."""
    
    if len(sys.argv) < 3:
        print("Usage: python entropy_analyzer.py <original_file> <encrypted_file>")
        print("\nExample:")
        print("  python entropy_analyzer.py mr_robot.jpg mr_robot.jpg.enc")
        sys.exit(1)
    
    original_path = sys.argv[1]
    encrypted_path = sys.argv[2]
    
    try:
        # Analyze both files
        original_results = analyze_file(original_path, is_encrypted=False)
        encrypted_results = analyze_file(encrypted_path, is_encrypted=True)
        
        # Print results
        print_results(original_results, encrypted_results)
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
