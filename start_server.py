"""
Start the Conut AI API server with clear progress indicators
"""
import sys
import subprocess

print("\n" + "="*70)
print("🚀 STARTING CONUT AI API SERVER")
print("="*70)
print("\n📍 Server will be available at: http://localhost:8000")
print("📚 API Documentation: http://localhost:8000/docs")
print("\n⏳ Starting up (this takes ~10-15 seconds)...\n")

# Run main.py and show output in real-time
try:
    subprocess.run([sys.executable, "main.py"], check=True)
except KeyboardInterrupt:
    print("\n\n🛑 Server stopped by user (Ctrl+C)")
except subprocess.CalledProcessError as e:
    print(f"\n\n❌ Server failed to start: {e}")
    sys.exit(1)
