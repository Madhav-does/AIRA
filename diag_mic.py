import speech_recognition as sr
import pyaudio

# List all microphones
mics = sr.Microphone.list_microphone_names()
print('=== MICROPHONES ===')
for i, m in enumerate(mics):
    print(f'  [{i}] {m}')

# Check default
pa = pyaudio.PyAudio()
try:
    dev = pa.get_default_input_device_info()
    print('=== DEFAULT INPUT DEVICE ===')
    print(f'  Index: {dev["index"]}')
    print(f'  Name:  {dev["name"]}')
    print(f'  Rate:  {dev["defaultSampleRate"]}')
except Exception as e:
    print(f'Default input error: {e}')
pa.terminate()

# Quick live listen test
print('\n=== QUICK LISTEN TEST (3 sec) ===')
r = sr.Recognizer()
r.energy_threshold = 200
r.dynamic_energy_threshold = True
try:
    with sr.Microphone() as src:
        r.adjust_for_ambient_noise(src, duration=1)
        print(f'Energy threshold after calibration: {r.energy_threshold:.1f}')
        print('Say something now...')
        audio = r.listen(src, timeout=5, phrase_time_limit=8)
    result = r.recognize_google(audio, language='en-IN')
    print(f'Heard: {result}')
except sr.WaitTimeoutError:
    print('No speech detected.')
except sr.UnknownValueError:
    print('Audio captured but could not understand it.')
except sr.RequestError as e:
    print(f'STT API error: {e}')
except Exception as e:
    print(f'Error: {e}')
