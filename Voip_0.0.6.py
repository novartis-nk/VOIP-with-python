import socket
import threading
import time
import numpy as np
import scipy.signal
import struct
import pyaudio
import logging

# Configurable parameters
CONFIG = {
    "sampling_rate": 48000,  # Increased sampling rate for better quality
    "target_sample_rate": 48000,  # Change the sample rate
    "quantization_bits": 16,  # Keep at 16 for balance between quality and performance
    "compression_enabled": False,  # Disable compression to maintain quality
    "echo_cancellation": True,  # Enable echo cancellation
    "silence_suppression": False,  # Disable silence suppression to avoid interruptions
    "vocoder_type": "Opus",  # Use Opus for superior quality
    "bit_rate": 128,  # Increased for better quality
    "frame_duration": 10,
    "udp_ip": "127.0.0.1",
    "udp_port": 5060,
    "packet_interval": 0.01, # Reduced interval for smoother audio
    "max_udp_size": 1472  # Max size of UDP payload (accounting for IP and UDP headers)
}

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Initialize PyAudio
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
    """Capture audio data from the microphone."""
    try:
        data = transmit_stream.read(4096, exception_on_overflow=False)
        return np.frombuffer(data, dtype=np.int16)
    except Exception as e:
        logging.error(f"Error capturing audio: {e}")
        return np.zeros(4096, dtype=np.int16)

# Part 2: Filter Frequencies
def filter_frequencies(voice_data):
    """Filter out frequencies outside the human voice range."""
    nyquist = CONFIG['sampling_rate'] / 2
    low, high = max(0.01, 300 / nyquist), min(0.99, 3400 / nyquist)
    b, a = scipy.signal.butter(4, [low, high], btype='band')
    return scipy.signal.lfilter(b, a, voice_data)

# Part 3: Sample Voice Data
def sample_voice(voice_data):
    """Resample voice data to the target sample rate."""
    if CONFIG['target_sample_rate'] != CONFIG['sampling_rate']:
        resample_factor = CONFIG['target_sample_rate'] / CONFIG['sampling_rate']
        new_length = int(len(voice_data) * resample_factor)
        return scipy.signal.resample(voice_data, new_length)
    return voice_data  # No resampling needed if rates are the same

# Part 4: Quantization
def quantize_voice(voice_data):
    """Quantize voice data for transmission."""
    max_val = 2 ** (CONFIG['quantization_bits'] - 1) - 1
    return np.clip(np.round(voice_data * max_val / np.max(np.abs(voice_data))), -max_val, max_val).astype(np.int16)

# Part 5: Digital Encoding into Bytes
def encode_to_bytes(quantized_data):
    """Convert quantized data to bytes."""
    return struct.pack(f'{len(quantized_data)}h', *quantized_data)

# Part 6: (Optional) Echo Cancellation
def apply_echo_cancellation(encoded_data):
    """Placeholder for echo cancellation; requires proper implementation."""
    if CONFIG['echo_cancellation']:
        logging.info("Echo cancellation applied (placeholder)")
    return encoded_data

# Part 7: (Optional) Silence Suppression
def apply_silence_suppression(encoded_data):
    """Placeholder for silence suppression."""
    if CONFIG['silence_suppression']:
        logging.info("Silence suppression applied (placeholder)")
    return encoded_data

# Part 8: (Optional) Compression
def compress_voice(encoded_data):
    """Placeholder for compression; example of downsampling."""
    if CONFIG['compression_enabled']:
        logging.info("Applying compression (placeholder)")
        return encoded_data[::2]  # Simple downsample as placeholder
    return encoded_data

# Part 9: Packetize Voice Data (RTP)
def packetize_rtp(encoded_data):
    """Packetize data into RTP format."""
    rtp_header = struct.pack("!BBHII", 0x80, 96, 0, 0, 0)  # Simple RTP header placeholder
    return rtp_header + encoded_data

# Part 10: Encapsulate in UDP Packet
def encapsulate_udp(rtp_packet):
    """Chunk RTP packet to fit within UDP constraints."""
    return [rtp_packet[i:i + CONFIG['max_udp_size']] for i in range(0, len(rtp_packet), CONFIG['max_udp_size'])]

# Part 11: Transmit Voice over IP
def transmit_voice(udp_chunks):
    """Transmit chunks over UDP."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for chunk in udp_chunks:
            sock.sendto(chunk, (CONFIG['udp_ip'], CONFIG['udp_port']))
        logging.info("Voice data transmitted.")

# VoIP Service Cycle
def voip_service():
    """Continuous cycle of capturing, processing, and transmitting voice."""
    while True:
        logging.info("Starting new transmission cycle.")
        voice_data = capture_analog_voice()
        voice_data = filter_frequencies(voice_data)
        voice_data = sample_voice(voice_data) 
        quantized_data = quantize_voice(voice_data)
        encoded_data = encode_to_bytes(quantized_data)
        encoded_data = apply_echo_cancellation(encoded_data)
        encoded_data = apply_silence_suppression(encoded_data)
        compressed_data = compress_voice(encoded_data)
        rtp_packet = packetize_rtp(compressed_data)
        udp_chunks = encapsulate_udp(rtp_packet)
        transmit_voice(udp_chunks)
        time.sleep(CONFIG['packet_interval'])

# Start VoIP service on a separate thread
voip_thread = threading.Thread(target=voip_service, daemon=True)
voip_thread.start()

# VoIP Receiver for Playback
def voip_receiver():
    """Receive and play incoming voice packets."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("0.0.0.0", CONFIG['udp_port']))
        while True:
            data, addr = sock.recvfrom(CONFIG['max_udp_size'])
            logging.info(f"Received packet from {addr}")
            audio_data = data[12:]  # Assuming 12 bytes for RTP header
            play_audio(audio_data)

def play_audio(audio_data):
    """Play audio data through speakers."""
    try:
        receive_stream.write(audio_data)
    except Exception as e:
        logging.error(f"Error playing audio: {e}")

# Start VoIP receiver on a separate thread
receiver_thread = threading.Thread(target=voip_receiver, daemon=True)
receiver_thread.start()

# Keep the main thread alive
while True:
    time.sleep(1)
