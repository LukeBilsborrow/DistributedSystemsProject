# Distributed Audio Transcription System

This project demonstrates a distributed system for audio transcription, designed as part of a university final year project. It allows users to upload an audio file via a web interface, process the audio to generate a transcription, and return the results. The system showcases various skills in distributed systems, web development, and audio processing.

This project is not fully polished, and certain areas could be improved or reworked in a professional setting. However, it highlights a broad range of technical skills and an understanding of distributed systems.

## Technologies
  - RabbitMQ
  - Django
  - Whisper (OpenAI)
  - Python
  - Javascript

## Overview

The system is divided into five independent components:

1. **Website**  
   - Users upload audio files and manage processing through a credit-based system (credits depend on audio length).
   - Displays results after processing.

2. **RabbitMQ Queue**  
   - Acts as a message broker, managing communication between the system's components.

3. **Processing Server (s2_worker)**  
   - Reads processing requests from the queue.
   - Processes audio files using an audio transcription pipeline.
   - Sends processed results back to the queue.

4. **Queue Sender (s1_queue_sender)**  
   - Receives data from the website and sends processing jobs to the RabbitMQ queue.

5. **Queue Reader (s1_queue_reader)**  
   - Retrieves processed results from the queue.
   - Sends the transcription back to the website for display.