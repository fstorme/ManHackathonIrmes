import numpy as np

def timestamp_to_seconds(timestamp):
    timestamp_split = timestamp.split(':')
    minutes = int(timestamp_split[1])
    timestamp_split = timestamp_split[2].split('.')
    seconds = int(timestamp_split[0])
    milliseconds = int(timestamp_split[1])
    return 60*minutes + seconds + milliseconds/1000

def x_stats_to_track(x, pitchLength):
    if np.abs(x)<=42:
        return (pitchLength-33)/84 * x
    elif x > 42:
        return 16.5/18 * (x-42) + pitchLength/2 - 16.5
    else:
        return 16.5/18 * (x+42) - pitchLength/2 + 16.5

def y_stats_to_track(y, pitchWidth):
    if np.abs(y)<=22:
        return 20.15/22 * y
    elif y > 22:
        return (pitchWidth/2 - 20.15) / 18 * (y-22) + 20.15
    else:
        return (pitchWidth/2 - 20.15) / 18 * (y+22) - 20.15