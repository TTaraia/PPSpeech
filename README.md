# Tigrinya narration

1. Save your text as `speech_ti.txt` in this folder (UTF-8) and put the folder in a GitHub repository.
2. `python speak_tigrinya.py --dry-run` shows the cleaned sentences and warnings (works anywhere, no voice needed). Fix the text first.
3. Actions > "Narrate Tigrinya text" > Run workflow. Download speech_ti.mp3, speech_ti.srt (YouTube subtitles) and speech_ti.clean.txt.

Voices: there is no free Tigrinya voice with a choice of gender.
- mms: Meta MMS (facebook/mms-tts-tir). One robotic voice, gender unknown until you listen. Licence CC-BY-NC 4.0 = NON-COMMERCIAL
  (a monetised YouTube channel counts as commercial). Use --lower 2..4 to make it deeper if it sounds too high.
- amharic: Amharic male voice (am-ET-AmehaNeural) reading Tigrinya letters. Experiment only: Tigrinya has sounds and letters
  Amharic lacks, so words get mispronounced.
- Best quality: a human narrator. Record the audio and use the .srt for subtitles.
