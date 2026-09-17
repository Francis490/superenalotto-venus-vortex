"""
build_history_2026.py
Garantisce che venus_history.json contenga TUTTI i concorsi 2026 (1-148).
Funziona in modalità MERGE: aggiunge solo i mancanti, non sovrascrive.

Così non perde i dati 2025 importati con import_external_history.py.
"""
import json
import os

HISTORY_FILE = "venus_history.json"


# ==========================================
# STORICO COMPLETO 2026 (148 concorsi)
# ==========================================
REAL_DRAWS_2026 = [
    # --- GENNAIO 2026 ---
    {"concorso": 1,  "data": "02/01/2026", "combinazione": [29, 33, 47, 56, 69, 89], "jolly": 16, "superstar": 7},
    {"concorso": 2,  "data": "03/01/2026", "combinazione": [16, 30, 32, 43, 68, 76], "jolly": 36, "superstar": 58},
    {"concorso": 3,  "data": "05/01/2026", "combinazione": [11, 13, 17, 56, 80, 84], "jolly": 41, "superstar": 13},
    {"concorso": 4,  "data": "08/01/2026", "combinazione": [35, 42, 45, 53, 55, 88], "jolly": 66, "superstar": 52},
    {"concorso": 5,  "data": "09/01/2026", "combinazione": [31, 33, 61, 68, 71, 72], "jolly": 87, "superstar": 18},
    {"concorso": 6,  "data": "10/01/2026", "combinazione": [11, 19, 24, 66, 82, 88], "jolly": 58, "superstar": 48},
    {"concorso": 7,  "data": "12/01/2026", "combinazione": [1, 11, 40, 73, 75, 81],  "jolly": 70, "superstar": 22},
    {"concorso": 8,  "data": "13/01/2026", "combinazione": [20, 29, 56, 68, 72, 74], "jolly": 35, "superstar": 50},
    {"concorso": 9,  "data": "15/01/2026", "combinazione": [44, 49, 60, 69, 73, 85], "jolly": 36, "superstar": 1},
    {"concorso": 10, "data": "16/01/2026", "combinazione": [14, 21, 24, 52, 80, 86], "jolly": 57, "superstar": 14},
    {"concorso": 11, "data": "17/01/2026", "combinazione": [3, 7, 41, 56, 65, 83],   "jolly": 79, "superstar": 82},
    {"concorso": 12, "data": "20/01/2026", "combinazione": [8, 13, 25, 60, 72, 74],  "jolly": 78, "superstar": 34},
    {"concorso": 13, "data": "22/01/2026", "combinazione": [2, 30, 52, 56, 57, 78],  "jolly": 59, "superstar": 25},
    {"concorso": 14, "data": "23/01/2026", "combinazione": [2, 6, 11, 19, 88, 90],   "jolly": 69, "superstar": 52},
    {"concorso": 15, "data": "24/01/2026", "combinazione": [22, 37, 55, 61, 68, 71], "jolly": 21, "superstar": 18},
    {"concorso": 16, "data": "27/01/2026", "combinazione": [11, 19, 27, 31, 54, 84], "jolly": 38, "superstar": 37},
    {"concorso": 17, "data": "29/01/2026", "combinazione": [29, 30, 34, 56, 66, 80], "jolly": 88, "superstar": 11},
    {"concorso": 18, "data": "30/01/2026", "combinazione": [32, 33, 39, 40, 52, 86], "jolly": 63, "superstar": 16},
    {"concorso": 19, "data": "31/01/2026", "combinazione": [2, 6, 7, 32, 37, 60],    "jolly": 11, "superstar": 80},

    # --- FEBBRAIO 2026 ---
    {"concorso": 20, "data": "03/02/2026", "combinazione": [11, 16, 17, 41, 42, 46], "jolly": 70, "superstar": 57},
    {"concorso": 21, "data": "05/02/2026", "combinazione": [6, 8, 26, 27, 57, 90],   "jolly": 41, "superstar": 30},
    {"concorso": 22, "data": "06/02/2026", "combinazione": [6, 8, 17, 31, 36, 75],   "jolly": 90, "superstar": 82},
    {"concorso": 23, "data": "07/02/2026", "combinazione": [4, 7, 12, 30, 69, 81],   "jolly": 41, "superstar": 67},
    {"concorso": 24, "data": "10/02/2026", "combinazione": [1, 15, 29, 39, 63, 83],  "jolly": 73, "superstar": 21},
    {"concorso": 25, "data": "12/02/2026", "combinazione": [5, 11, 35, 52, 80, 85],  "jolly": 66, "superstar": 29},
    {"concorso": 26, "data": "13/02/2026", "combinazione": [1, 52, 57, 71, 76, 83],  "jolly": 37, "superstar": 3},
    {"concorso": 27, "data": "14/02/2026", "combinazione": [5, 23, 40, 47, 80, 85],  "jolly": 6, "superstar": 47},
    {"concorso": 28, "data": "17/02/2026", "combinazione": [16, 21, 42, 45, 52, 88], "jolly": 58, "superstar": 21},
    {"concorso": 29, "data": "19/02/2026", "combinazione": [20, 39, 40, 43, 76, 90], "jolly": 53, "superstar": 53},
    {"concorso": 30, "data": "20/02/2026", "combinazione": [30, 34, 41, 42, 49, 83], "jolly": 64, "superstar": 77},
    {"concorso": 31, "data": "21/02/2026", "combinazione": [49, 58, 60, 66, 68, 81], "jolly": 75, "superstar": 58},
    {"concorso": 32, "data": "24/02/2026", "combinazione": [4, 18, 23, 26, 45, 87],  "jolly": 82, "superstar": 29},
    {"concorso": 33, "data": "26/02/2026", "combinazione": [18, 30, 36, 52, 67, 72], "jolly": 69, "superstar": 47},
    {"concorso": 34, "data": "27/02/2026", "combinazione": [10, 14, 49, 55, 71, 79], "jolly": 80, "superstar": 36},
    {"concorso": 35, "data": "28/02/2026", "combinazione": [14, 17, 33, 63, 64, 80], "jolly": 15, "superstar": 27},

    # --- MARZO 2026 ---
    {"concorso": 36, "data": "03/03/2026", "combinazione": [4, 16, 42, 48, 56, 68],  "jolly": 26, "superstar": 83},
    {"concorso": 37, "data": "05/03/2026", "combinazione": [7, 23, 39, 62, 63, 78],  "jolly": 22, "superstar": 35},
    {"concorso": 38, "data": "06/03/2026", "combinazione": [4, 17, 22, 37, 50, 88],  "jolly": 20, "superstar": 2},
    {"concorso": 39, "data": "07/03/2026", "combinazione": [3, 12, 18, 40, 45, 69],  "jolly": 5, "superstar": 49},
    {"concorso": 40, "data": "10/03/2026", "combinazione": [8, 34, 42, 47, 55, 83],  "jolly": 4, "superstar": 42},
    {"concorso": 41, "data": "12/03/2026", "combinazione": [8, 24, 25, 62, 63, 64],  "jolly": 43, "superstar": 54},
    {"concorso": 42, "data": "13/03/2026", "combinazione": [3, 11, 13, 20, 53, 61],  "jolly": 88, "superstar": 43},
    {"concorso": 43, "data": "14/03/2026", "combinazione": [3, 6, 33, 63, 88, 89],   "jolly": 18, "superstar": 87},
    {"concorso": 44, "data": "17/03/2026", "combinazione": [2, 13, 16, 41, 53, 56],  "jolly": 60, "superstar": 6},
    {"concorso": 45, "data": "19/03/2026", "combinazione": [19, 39, 45, 54, 62, 89], "jolly": 42, "superstar": 45},
    {"concorso": 46, "data": "20/03/2026", "combinazione": [14, 32, 45, 51, 54, 87], "jolly": 61, "superstar": 50},
    {"concorso": 47, "data": "21/03/2026", "combinazione": [9, 26, 33, 49, 51, 55],  "jolly": 50, "superstar": 4},
    {"concorso": 48, "data": "24/03/2026", "combinazione": [6, 54, 60, 64, 74, 87],  "jolly": 10, "superstar": 65},
    {"concorso": 49, "data": "26/03/2026", "combinazione": [24, 26, 39, 69, 77, 80], "jolly": 82, "superstar": 3},
    {"concorso": 50, "data": "27/03/2026", "combinazione": [6, 22, 27, 43, 58, 64],  "jolly": 10, "superstar": 74},
    {"concorso": 51, "data": "28/03/2026", "combinazione": [9, 45, 62, 67, 68, 81],  "jolly": 36, "superstar": 54},
    {"concorso": 52, "data": "31/03/2026", "combinazione": [1, 3, 39, 46, 47, 61],   "jolly": 25, "superstar": 67},

    # --- APRILE 2026 ---
    {"concorso": 53, "data": "02/04/2026", "combinazione": [18, 24, 25, 32, 36, 63], "jolly": 40, "superstar": 80},
    {"concorso": 54, "data": "03/04/2026", "combinazione": [28, 52, 53, 64, 66, 72], "jolly": 44, "superstar": 6},
    {"concorso": 55, "data": "04/04/2026", "combinazione": [8, 21, 29, 46, 60, 81],  "jolly": 42, "superstar": 80},
    {"concorso": 56, "data": "07/04/2026", "combinazione": [10, 16, 18, 47, 50, 59], "jolly": 7, "superstar": 60},
    {"concorso": 57, "data": "09/04/2026", "combinazione": [2, 30, 38, 63, 74, 84],  "jolly": 19, "superstar": 82},
    {"concorso": 58, "data": "10/04/2026", "combinazione": [3, 10, 13, 17, 58, 90],  "jolly": 32, "superstar": 7},
    {"concorso": 59, "data": "11/04/2026", "combinazione": [19, 28, 38, 48, 77, 85], "jolly": 59, "superstar": 57},
    {"concorso": 60, "data": "14/04/2026", "combinazione": [3, 5, 20, 27, 35, 66],   "jolly": 17, "superstar": 6},
    {"concorso": 61, "data": "16/04/2026", "combinazione": [9, 11, 12, 38, 44, 54],  "jolly": 60, "superstar": 39},
    {"concorso": 62, "data": "17/04/2026", "combinazione": [13, 27, 45, 53, 57, 84], "jolly": 34, "superstar": 63},
    {"concorso": 63, "data": "18/04/2026", "combinazione": [11, 22, 28, 33, 68, 77], "jolly": 9, "superstar": 70},
    {"concorso": 64, "data": "21/04/2026", "combinazione": [18, 19, 40, 43, 56, 77], "jolly": 6, "superstar": 65},
    {"concorso": 65, "data": "23/04/2026", "combinazione": [18, 24, 28, 35, 56, 58], "jolly": 72, "superstar": 57},
    {"concorso": 66, "data": "24/04/2026", "combinazione": [6, 13, 33, 37, 68, 82],  "jolly": 56, "superstar": 20},
    {"concorso": 67, "data": "27/04/2026", "combinazione": [40, 57, 62, 64, 85, 87], "jolly": 23, "superstar": 56},
    {"concorso": 68, "data": "28/04/2026", "combinazione": [29, 42, 43, 47, 57, 60], "jolly": 27, "superstar": 30},
    {"concorso": 69, "data": "30/04/2026", "combinazione": [6, 7, 15, 44, 52, 58],   "jolly": 40, "superstar": 16},

    # --- MAGGIO 2026 ---
    {"concorso": 70, "data": "02/05/2026", "combinazione": [7, 58, 60, 79, 84, 86],  "jolly": 2, "superstar": 19},
    {"concorso": 71, "data": "04/05/2026", "combinazione": [3, 14, 31, 46, 61, 63],  "jolly": 75, "superstar": 24},
    {"concorso": 72, "data": "05/05/2026", "combinazione": [24, 34, 45, 55, 81, 87], "jolly": 23, "superstar": 52},
    {"concorso": 73, "data": "07/05/2026", "combinazione": [1, 34, 48, 66, 69, 73],  "jolly": 75, "superstar": 58},
    {"concorso": 74, "data": "08/05/2026", "combinazione": [8, 16, 41, 47, 51, 90],  "jolly": 82, "superstar": 69},
    {"concorso": 75, "data": "09/05/2026", "combinazione": [9, 27, 30, 42, 43, 62],  "jolly": 11, "superstar": 11},
    {"concorso": 76, "data": "12/05/2026", "combinazione": [2, 28, 31, 57, 58, 59],  "jolly": 5, "superstar": 2},
    {"concorso": 77, "data": "14/05/2026", "combinazione": [31, 56, 72, 74, 84, 85], "jolly": 18, "superstar": 34},
    {"concorso": 78, "data": "15/05/2026", "combinazione": [5, 13, 17, 28, 47, 68],  "jolly": 42, "superstar": 19},
    {"concorso": 79, "data": "16/05/2026", "combinazione": [7, 12, 60, 69, 89, 90],  "jolly": 59, "superstar": 36},
    {"concorso": 80, "data": "19/05/2026", "combinazione": [49, 57, 61, 73, 79, 86], "jolly": 8, "superstar": 36},
    {"concorso": 81, "data": "21/05/2026", "combinazione": [1, 38, 57, 58, 64, 81],  "jolly": 28, "superstar": 50},
    {"concorso": 82, "data": "22/05/2026", "combinazione": [5, 17, 65, 71, 83, 87],  "jolly": 50, "superstar": 86},
    {"concorso": 83, "data": "23/05/2026", "combinazione": [14, 29, 34, 57, 59, 69], "jolly": 20, "superstar": 16},
    {"concorso": 84, "data": "26/05/2026", "combinazione": [7, 10, 35, 41, 45, 61],  "jolly": 2, "superstar": 45},
    {"concorso": 85, "data": "28/05/2026", "combinazione": [22, 33, 36, 74, 78, 86], "jolly": 81, "superstar": 34},
    {"concorso": 86, "data": "29/05/2026", "combinazione": [9, 42, 44, 46, 85, 90],  "jolly": 56, "superstar": 20},
    {"concorso": 87, "data": "30/05/2026", "combinazione": [8, 13, 21, 39, 63, 71],  "jolly": 72, "superstar": 56},

    # --- GIUGNO 2026 ---
    {"concorso": 88, "data": "04/06/2026", "combinazione": [12, 33, 43, 55, 74, 75], "jolly": 70, "superstar": 59},
    {"concorso": 89, "data": "05/06/2026", "combinazione": [9, 25, 51, 63, 73, 89],  "jolly": 90, "superstar": 40},
    {"concorso": 90, "data": "06/06/2026", "combinazione": [2, 7, 29, 68, 72, 89],   "jolly": 57, "superstar": 38},
    {"concorso": 91, "data": "08/06/2026", "combinazione": [28, 33, 51, 59, 82, 87], "jolly": 88, "superstar": 87},
    {"concorso": 92, "data": "09/06/2026", "combinazione": [18, 36, 47, 55, 73, 80], "jolly": 90, "superstar": 54},
    {"concorso": 93, "data": "11/06/2026", "combinazione": [7, 21, 22, 40, 44, 87],  "jolly": 53, "superstar": 83},
    {"concorso": 94, "data": "12/06/2026", "combinazione": [18, 24, 42, 68, 75, 83], "jolly": 26, "superstar": 20},
    {"concorso": 95, "data": "13/06/2026", "combinazione": [13, 23, 34, 68, 87, 90], "jolly": 80, "superstar": 54},
    {"concorso": 96, "data": "16/06/2026", "combinazione": [4, 28, 33, 35, 66, 80],  "jolly": 48, "superstar": 72},
    {"concorso": 97, "data": "18/06/2026", "combinazione": [4, 26, 39, 43, 70, 87],  "jolly": 57, "superstar": 57},
    {"concorso": 98, "data": "19/06/2026", "combinazione": [14, 18, 25, 69, 81, 89], "jolly": 11, "superstar": 69},
    {"concorso": 99, "data": "20/06/2026", "combinazione": [14, 59, 69, 71, 82, 89], "jolly": 47, "superstar": 3},
    {"concorso": 100, "data": "23/06/2026", "combinazione": [1, 12, 17, 27, 66, 84], "jolly": 61, "superstar": 4},
    {"concorso": 101, "data": "25/06/2026", "combinazione": [25, 27, 54, 72, 73, 76], "jolly": 31, "superstar": 80},
    {"concorso": 102, "data": "26/06/2026", "combinazione": [1, 22, 30, 45, 73, 76], "jolly": 64, "superstar": 49},
    {"concorso": 103, "data": "27/06/2026", "combinazione": [15, 19, 36, 47, 85, 90], "jolly": 42, "superstar": 62},
    {"concorso": 104, "data": "30/06/2026", "combinazione": [1, 7, 51, 64, 78, 83],   "jolly": 13, "superstar": 66},

    # --- LUGLIO 2026 ---
    {"concorso": 105, "data": "02/07/2026", "combinazione": [4, 17, 19, 23, 47, 59],  "jolly": 51, "superstar": 82},
    {"concorso": 106, "data": "03/07/2026", "combinazione": [22, 26, 30, 40, 68, 86], "jolly": 72, "superstar": 48},
    {"concorso": 107, "data": "04/07/2026", "combinazione": [2, 37, 55, 62, 72, 76],  "jolly": 34, "superstar": 75},
    {"concorso": 108, "data": "07/07/2026", "combinazione": [3, 16, 30, 53, 55, 79],  "jolly": 84, "superstar": 66},
    {"concorso": 109, "data": "09/07/2026", "combinazione": [9, 17, 20, 31, 40, 79],  "jolly": 58, "superstar": 47},
    {"concorso": 110, "data": "10/07/2026", "combinazione": [2, 3, 12, 28, 63, 82],   "jolly": 76, "superstar": 79},
    {"concorso": 111, "data": "11/07/2026", "combinazione": [6, 7, 10, 47, 49, 61],   "jolly": 5, "superstar": 62},
    {"concorso": 112, "data": "14/07/2026", "combinazione": [8, 44, 49, 80, 85, 88],  "jolly": 30, "superstar": 64},
    {"concorso": 113, "data": "16/07/2026", "combinazione": [1, 15, 21, 46, 52, 67],  "jolly": 41, "superstar": 76},
    {"concorso": 114, "data": "17/07/2026", "combinazione": [7, 34, 45, 64, 65, 76],  "jolly": 46, "superstar": 90},
    {"concorso": 115, "data": "18/07/2026", "combinazione": [1, 28, 52, 62, 79, 86],  "jolly": 61, "superstar": 31},
    {"concorso": 116, "data": "21/07/2026", "combinazione": [13, 14, 15, 29, 38, 63], "jolly": 24, "superstar": 49},
    {"concorso": 117, "data": "23/07/2026", "combinazione": [2, 12, 22, 34, 70, 74],  "jolly": 41, "superstar": 8},
    {"concorso": 118, "data": "24/07/2026", "combinazione": [20, 40, 53, 61, 74, 79], "jolly": 11, "superstar": 30},
    {"concorso": 119, "data": "25/07/2026", "combinazione": [18, 19, 33, 34, 61, 85], "jolly": 15, "superstar": 59},
    {"concorso": 120, "data": "28/07/2026", "combinazione": [1, 6, 9, 43, 54, 62],   "jolly": 87, "superstar": 69},
    {"concorso": 121, "data": "30/07/2026", "combinazione": [20, 47, 75, 76, 78, 89], "jolly": 9, "superstar": 89},
    {"concorso": 122, "data": "31/07/2026", "combinazione": [2, 6, 10, 31, 39, 83],  "jolly": 66, "superstar": 75},

    # --- AGOSTO 2026 ---
    {"concorso": 123, "data": "01/08/2026", "combinazione": [8, 11, 21, 24, 72, 88],  "jolly": 33, "superstar": 11},
    {"concorso": 124, "data": "04/08/2026", "combinazione": [49, 56, 58, 70, 76, 78], "jolly": 29, "superstar": 16},
    {"concorso": 125, "data": "06/08/2026", "combinazione": [2, 11, 20, 33, 74, 83],  "jolly": 15, "superstar": 19},
    {"concorso": 126, "data": "07/08/2026", "combinazione": [1, 7, 29, 32, 60, 63],   "jolly": 68, "superstar": 37},
    {"concorso": 127, "data": "08/08/2026", "combinazione": [9, 12, 55, 61, 82, 85],  "jolly": 71, "superstar": 31},
    {"concorso": 128, "data": "11/08/2026", "combinazione": [8, 19, 38, 53, 66, 79],  "jolly": 90, "superstar": 49},
    {"concorso": 129, "data": "13/08/2026", "combinazione": [2, 7, 16, 29, 57, 84],   "jolly": 18, "superstar": 1},
    {"concorso": 130, "data": "14/08/2026", "combinazione": [9, 18, 20, 25, 53, 90],  "jolly": 49, "superstar": 23},
    {"concorso": 131, "data": "17/08/2026", "combinazione": [18, 24, 69, 71, 73, 82], "jolly": 29, "superstar": 41},
    {"concorso": 132, "data": "18/08/2026", "combinazione": [10, 16, 24, 25, 39, 66], "jolly": 70, "superstar": 6},
    {"concorso": 133, "data": "20/08/2026", "combinazione": [14, 18, 26, 51, 64, 71], "jolly": 77, "superstar": 49},
    {"concorso": 134, "data": "21/08/2026", "combinazione": [12, 25, 27, 28, 39, 57], "jolly": 42, "superstar": 13},
    {"concorso": 135, "data": "22/08/2026", "combinazione": [2, 16, 23, 31, 72, 85],  "jolly": 82, "superstar": 14},
    {"concorso": 136, "data": "25/08/2026", "combinazione": [15, 36, 62, 67, 69, 70], "jolly": 32, "superstar": 15},
    {"concorso": 137, "data": "27/08/2026", "combinazione": [2, 27, 28, 50, 75, 84],  "jolly": 32, "superstar": 40},
    {"concorso": 138, "data": "28/08/2026", "combinazione": [4, 8, 27, 62, 70, 79],   "jolly": 60, "superstar": 55},
    {"concorso": 139, "data": "29/08/2026", "combinazione": [12, 17, 45, 59, 74, 77], "jolly": 62, "superstar": 62},

    # --- SETTEMBRE 2026 ---
    {"concorso": 140, "data": "01/09/2026", "combinazione": [42, 47, 59, 64, 67, 71], "jolly": 88, "superstar": 75},
    {"concorso": 141, "data": "03/09/2026", "combinazione": [8, 11, 15, 60, 68, 76],  "jolly": 9, "superstar": 90},
    {"concorso": 142, "data": "04/09/2026", "combinazione": [8, 44, 60, 73, 86, 89],  "jolly": 57, "superstar": 42},
    {"concorso": 143, "data": "05/09/2026", "combinazione": [12, 24, 28, 32, 37, 78], "jolly": 40, "superstar": 16},
    {"concorso": 144, "data": "08/09/2026", "combinazione": [23, 26, 41, 52, 59, 85], "jolly": 49, "superstar": 47},
    {"concorso": 145, "data": "10/09/2026", "combinazione": [2, 17, 39, 59, 63, 89],  "jolly": 62, "superstar": 62},
    {"concorso": 146, "data": "11/09/2026", "combinazione": [8, 13, 16, 52, 64, 70],  "jolly": 17, "superstar": 21},
    {"concorso": 147, "data": "12/09/2026", "combinazione": [3, 7, 14, 40, 78, 81],   "jolly": 1, "superstar": 54},
    {"concorso": 148, "data": "15/09/2026", "combinazione": [3, 12, 18, 32, 47, 54],  "jolly": 69, "superstar": 28},
]


def parse_date(date_str):
    """Ritorna (YYYY, MM, DD) per ordinamento cronologico."""
    from datetime import datetime
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return (dt.year, dt.month, dt.day)
    except Exception:
        return (0, 0, 0)


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Errore lettura: {e}")
    return []


def save_history(data):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[+] Salvato: {HISTORY_FILE}")
    except Exception as e:
        print(f"[!] Errore salvataggio: {e}")


def main():
    print("=== BUILD HISTORY 2026 (MERGE MODE) ===")

    # Leggi database esistente
    existing = load_history()
    print(f"[*] Database attuale: {len(existing)} concorsi")

    existing_ids = {item.get("concorso") for item in existing
                    if isinstance(item.get("concorso"), int)}

    # Aggiungi SOLO i 2026 mancanti
    to_add = [d for d in REAL_DRAWS_2026
              if d["concorso"] not in existing_ids]

    if not to_add:
        print("[*] Nessun concorso 2026 da aggiungere (già presenti).")
        print(f"[*] Totale: {len(existing)} concorsi")
        print("=== COMPLETATO ===")
        return

    print(f"[+] Aggiungo {len(to_add)} concorsi 2026 mancanti:")
    for d in to_add:
        print(f"    • {d['concorso']} ({d['data']})")

    # Merge
    merged = existing + to_add
    merged.sort(key=lambda x: parse_date(x.get("data", "")))

    # Verifica finale
    ids = [e["concorso"] for e in merged]
    ids_2026 = [i for i in ids if 1 <= i <= 148]
    ids_2025 = [i for i in ids if 1001 <= i <= 1208]

    print(f"\n[*] Totale finale: {len(merged)} concorsi")
    print(f"[*] Concorsi 2025: {len(set(ids_2025))} (atteso: 208)")
    print(f"[*] Concorsi 2026: {len(set(ids_2026))} (atteso: 148)")

    # Verifica buchi 2026
    expected_2026 = set(range(1, 149))
    actual_2026 = set(ids_2026)
    missing_2026 = sorted(expected_2026 - actual_2026)

    if missing_2026:
        print(f"[!] ATTENZIONE - Concorsi 2026 ancora mancanti: {missing_2026}")
    else:
        print(f"[✓] 2026 completo!")

    save_history(merged)
    print("=== COMPLETATO ===")


if __name__ == "__main__":
    main()
