#!/bin/bash
g++ process_a_gpu1.cpp -o capture_gpu1 -lGL -lGLU -lglut
g++ process_b_gpu2.cpp -o process_gpu2 -lGL -lGLU -lglut
