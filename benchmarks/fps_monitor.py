import mmap
import struct
import time

def read_native_fps():
 """Lee el FPS nativo desde memoria compartida"""
 try:
 with open('/dev/shm/framebuffer_shared', 'r+b') as f:
 # Mapear solo el header
 mm = mmap.mmap(f.fileno(), 32, access=mmap.ACCESS_READ)
            
 # Leer header: width, height, seq, status, fps (double)
 header = struct.unpack('IIII d', mm[:24])
 width, height, seq, status, native_fps = header
            
 mm.close()
            
 if status == 1 and native_fps > 0:
 return {
 'width': width,
 'height': height,
 'sequence': seq,
 'native_fps': native_fps,
 'timestamp': time.time()
 }
 except Exception as e:
 print(f"Error reading FPS: {e}")
    
 return None

def monitor_native_fps(duration=10):
 """Monitorea FPS nativo por X segundos"""
 print(" Monitoring native FPS...")
    
 fps_samples = []
 start_time = time.time()
    
 while time.time() - start_time < duration:
 fps_data = read_native_fps()
 if fps_data:
 fps_samples.append(fps_data['native_fps'])
 print(f"Native FPS: {fps_data['native_fps']:.1f} @ {fps_data['width']}x{fps_data['height']}")
        
 time.sleep(0.1)
    
 if fps_samples:
 avg_fps = sum(fps_samples) / len(fps_samples)
 print(f"\n Average Native FPS: {avg_fps:.2f}")
 return avg_fps
 else:
 print(" No FPS data captured")
 return 0.0

if __name__ == "__main__":
 monitor_native_fps(30) # Monitor por 30 segundos