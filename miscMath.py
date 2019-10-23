
import numpy as np



def getHeading(start_lat, start_lon, end_lat, end_lon):
    radians = np.arctan2(np.radians(end_lon - start_lon), np.radians(end_lat - start_lat))
    return np.degrees(radians)

def getDistance(start_lat, start_lon, end_lat, end_lon):
    earthRadiusMeters = 6371.0 * 1000.0
    dLat = np.radians(end_lat - start_lat)
    dLon = np.radians(end_lon - start_lon)
    eLat = np.radians(end_lat)
    sLat = np.radians(start_lat)
    a = np.sin(dLat/2) * np.sin(dLat/2) +\
          np.sin(dLon/2) * np.sin(dLon/2) * np.cos(eLat) * np.cos(sLat)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return earthRadiusMeters * c

def compareTwoAngles(fromAngle, toAngle):
    '''Mavlink gives us an angle that is +/- 180 degrees
        we want:  toAngle-fromAngle, but with wrap-around at +/- 180
    '''
    rotate = toAngle - fromAngle
    while rotate > 180.0:
        rotate -= 360.0
    while rotate < -180.0:
        rotate += 360.0
    return rotate


def get_line_coefficients(x0, x1, y0, y1):
    '''
    From two points, calculate "m" and "b" to be used in the
    line equation:  y = m*x + b
    '''
    m = (y1 - y0) / (x1 - x0)
    b = y0 - m * x0
    return m, b





