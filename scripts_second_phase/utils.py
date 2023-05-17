import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

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
    
def flip_coord_team(dict_num):
    return {key : [-values[0],-values[1],values[2]] for key, values in dict_num.items()}

def count_adversary_closer_to_goal(dict_num, dist_goal):
    return sum(
        np.sqrt((60 - values[0]) ** 2 + values[1] ** 2)
        < dist_goal
        for _, values in dict_num.items()
    )

def bypassed_opponents(dict_coord, x_passer, x_receiver):
    if x_passer>=x_receiver:
        return 0
    return sum(
        values[0] >= x_passer and values[0] <= x_receiver
        for _, values in dict_coord.items()
    )

def angle(x_passer, y_passer, x_receiver, y_receiver):
    if y_receiver>=y_passer:
        return np.arccos((x_receiver-x_passer)/np.sqrt((x_passer-x_receiver)**2+(y_passer-y_receiver)**2)) * 180/np.pi
    else:
        return -np.arccos((x_receiver-x_passer)/np.sqrt((x_passer-x_receiver)**2+(y_passer-y_receiver)**2)) * 180/np.pi
    
def opponents_in_path(x_passer, y_passer, x_receiver, y_receiver, dict_coord):
    x = x_receiver - x_passer
    y = y_receiver - y_passer
    if x!=0:
        theta = np.arctan(y/x)
    else:
        theta = np.pi/2 if y>=0 else -np.pi/2
    xa = -5*np.sin(theta)
    ya = 5*np.cos(theta)
    if x<0: 
        xa = -xa
        ya = -ya
    # print(xa,ya)
    polygon = Polygon([(x_passer+xa, y_passer+ya),(x_passer-xa,y_passer-ya),(x_receiver-xa, y_receiver-ya),(x_receiver+xa,y_receiver+ya)])
    return sum(
        bool(polygon.contains(Point(values[0], values[1])))
        for _, values in dict_coord.items()
    )

def nearest_defender_pass_line(x_passer, y_passer, x_receiver, y_receiver, dict_coord):
    #use of formula : https://math.stackexchange.com/questions/2757318/distance-between-a-point-and-a-line-defined-by-2-points
    min_dist = np.inf
    for _, values in dict_coord.items():
        numerator = abs((x_receiver - x_passer)*(values[1]-y_passer)-(y_receiver-y_passer)*(values[0]-x_passer))
        denumerator = np.sqrt((x_receiver-x_passer)**2 + (y_receiver-y_passer)**2)
        dist = numerator/denumerator
        min_dist = min(min_dist,dist)
    return min_dist

def flip_dictionnary(coord):
    return {key: [-val[0], -val[1], val[2:]] for key, val in coord.items()}
        