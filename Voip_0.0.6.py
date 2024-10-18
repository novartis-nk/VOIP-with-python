import socket
import threading
import time
import numpy as np
import scipy.signal
import struct
import pyaudio

# Updated Configurable parameters for better quality and performance
CONFIG = {
    "sampling_rate": 48000,  # Increased sampling rate for better quality
    "quantization_bits": 16,  # Keep at 16 for balance between quality and performance
    "compression_enabled": False,  # Disable compression to maintain quality
    "echo_cancellation": True,  # Enable echo cancellation
    "silence_suppression": False,  # Disable silence suppression to avoid interruptions
    "vocoder_type": "Opus",  # Use Opus for superior quality
    "bit_rate": 128,  # Increased for better quality
    "frame_duration": 10,
    "udp_ip": "127.0.0.1",
    "udp_port": 5060,
    "packet_interval": 0.02,  # Reduced interval for smoother audio
    "max_udp_size": 1472  # Max size of UDP payload (accounting for IP and UDP headers)
}

# Initialize PyAudio and Audio Streams with updated buffer size
audio = pyaudio.PyAudio()
transmit_stream = audio.open(format=pyaudio.paInt16,
                             channels=1,
                             rate=CONFIG['sampling_rate'],
                             input=True,
                             frames_per_buffer=8192)
receive_stream = audio.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=CONFIG['sampling_rate'],
                            output=True,
                            frames_per_buffer=8192)

# Part 1: Analog Voice Capture
def capture_analog_voice():
    print("Capturing analog voice...")
    try:
        data = transmit_stream.read(8192, exception_on_overflow=False)
    except Exception as e:
        print(f"Error capturing audio: {e}")
        data = np.zeros(8192, dtype=np.int16).tobytes()
    print("Captured analog voice.")
    return np.frombuffer(data, dtype=np.int16)

# Part 2: Filter Lower/Higher Frequencies
def filter_frequencies(voice_data):
    print("Filtering frequencies...")
    nyquist = CONFIG['sampling_rate'] / 2
    low = max(0.01, 300 / nyquist)
    high = min(0.99, 3400 / nyquist)
    b, a = scipy.signal.butter(4, [low, high], btype='band')
    filtered_data = scipy.signal.lfilter(b, a, voice_data)
    print("Filtered frequencies.")
    return filtered_data

# Part 3: Sample Voice Data
def sample_voice(voice_data):
    print("Sampling voice...")
    print("Sampled voice.")
    return voice_data

# Part 4: Quantization
def quantize_voice(sampled_data):
    print("Quantizing voice...")
    max_val = 2 ** (CONFIG['quantization_bits'] - 1) - 1
    quantized_data = np.clip(np.round(sampled_data * max_val / np.max(np.abs(sampled_data))), -max_val, max_val)
    print("Quantized voice.")
    return quantized_data.astype(np.int16)

# Part 5: Digital Encoding into Bytes
def encode_to_bytes(quantized_data):
    print("Encoding quantized data to bytes...")
    encoded_data = struct.pack(f'{len(quantized_data)}h', *quantized_data)
    print("Encoded quantized data to bytes.")
    return encoded_data

# Part 6: Echo Cancellation
def echo_cancellation(encoded_data):
    if CONFIG['echo_cancellation']:
        print("Applying echo cancellation...")
        # Simulate echo cancellation
        print("Applied echo cancellation.")
    return encoded_data

# Part 7: Silence Suppression (Optional)
def silence_suppression(encoded_data):
    if CONFIG['silence_suppression']:
        print("Applying silence suppression...")
        print("Applied silence suppression.")
    return encoded_data

# Part 8: Compression (Optional)
def compress_voice(encoded_data):
    if CONFIG['compression_enabled']:
        print("Compressing voice data...")
        compressed_data = encoded_data[::2]  # Example: downsample by 2 for compression
        print("Compressed voice data.")
    else:
        compressed_data = encoded_data
    return compressed_data

# Part 9: Packetize Voice Data (RTP)
def packetize_rtp(encoded_data):
    print("Packetizing voice data into RTP packet...")
    rtp_header = b'RTP_HEADER'  # Placeholder for RTP header
    rtp_packet = rtp_header + encoded_data
    print("Packetized voice data into RTP packet.")
    return rtp_packet

# Part 10: Encapsulate in UDP Packet
def encapsulate_udp(rtp_packet):
    print("Encapsulating RTP packet into UDP packet...")

    # Chunking the packet into smaller sizes
    max_size = CONFIG['max_udp_size']
    chunks = [rtp_packet[i:i + max_size] for i in range(0, len(rtp_packet), max_size)]
    
    print("Encapsulated RTP packet into UDP packet.")
    return chunks

# Part 11: Transmit Voice over IP
def transmit_voice(udp_chunks):
    print("Transmitting voice over IP...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = (CONFIG['udp_ip'], CONFIG['udp_port'])

    for chunk in udp_chunks:
        sock.sendto(chunk, addr)
    
    sock.close()
    print("Transmitted voice over IP.")

# Threaded function to simulate continuous transmission
def voip_service():
    while True:
        print("Starting new transmission cycle...")
        voice_data = capture_analog_voice()
        voice_data = filter_frequencies(voice_data)
        sampled_data = sample_voice(voice_data)
        quantized_data = quantize_voice(sampled_data)
        encoded_data = encode_to_bytes(quantized_data)
        encoded_data = echo_cancellation(encoded_data)
        encoded_data = silence_suppression(encoded_data)
        compressed_data = compress_voice(encoded_data)
        rtp_packet = packetize_rtp(compressed_data)
        udp_chunks = encapsulate_udp(rtp_packet)
        transmit_voice(udp_chunks)
        print("Transmission cycle completed.")
        time.sleep(CONFIG['packet_interval'])  # Transmission interval

# Start VoIP service on a separate thread
print("Starting VoIP service thread...")
voip_thread = threading.Thread(target=voip_service)
voip_thread.daemon = True
voip_thread.start()

# Receiver Code to Listen to Incoming Packets and Play Audio
def play_audio(audio_data):
    print("Playing received audio...")
    try:
        receive_stream.write(audio_data)
    except Exception as e:
        print(f"Error playing audio: {e}")
    print("Finished playing received audio.")

def voip_receiver():
    print("Starting VoIP receiver...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", CONFIG['udp_port']))

    while True:
        print("Waiting to receive packet...")
        data, addr = sock.recvfrom(CONFIG['max_udp_size'])
        print("Received packet from", addr)
        # Remove RTP header and play the audio
        audio_data = data[len(b'RTP_HEADER'):]
        play_audio(audio_data)

# Start VoIP receiver on a separate thread
print("Starting VoIP receiver thread...")
receiver_thread = threading.Thread(target=voip_receiver)
receiver_thread.daemon = True
receiver_thread.start()

# Keep the main thread alive
while True:
    time.sleep(1)
