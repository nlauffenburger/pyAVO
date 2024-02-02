"""
Google Encoded Polyline Algorithm:
    https://developers.google.com/maps/documentation/utilities/polylinealgorithm

Encoding algorithm for floats ripped from gPolyEncode:
    http://code.google.com/p/py-gpolyencode
"""

from io import StringIO
import numpy as np

def encode_float(value):

    enc_value = StringIO()
    int_value = int(value * 1e5) << 1

    if value < 0:
        int_value = ~int_value

    while int_value >= 0x20:
        ord_ = (0x20 | (int_value & 0x1F))  + 63
        enc_value.write(chr(ord_))
        int_value >>= 5

    int_value += 63
    enc_value.write(chr(int_value))
    return enc_value.getvalue()

def encode_line(line):
    enc_value = StringIO()
    
    for lat, lon in line:

        enc_value.write(encode_float(lat) + encode_float(lon))

    return enc_value.getvalue()



def decode_float(enc_value):

    num = 0
    for k in range(len(enc_value)):
        c = enc_value[k]
        chunk = (ord(c) - 63) & 0x1F
        num |= chunk << (5 * k)

    if num & 0x1:
        num = ~num

    num >>= 1

    return num * 1.0e-5


def decode_line(enc_line):

    #Find number breaks
    indx = []
    for y in enumerate(enc_line):
        #  find the spaces in the encoded data.
        #  first subtract 63 because of the encoding:
        #      https://developers.google.com/maps/documentation/utilities/polylinealgorithm
        #  Then bitwise and with ASCII space (hex 0x20) which returns 0 if teh char is a space
        #  Lastly not to return True when the char is a space
        if (not (ord(y[1]) - 63) & 0x20):
            #  append the index of this char to our list
            indx.append(y[0])


    n_coords = len(indx)
    tmp = [0] * n_coords
    lb = 0

    for k in range(n_coords ):
        ub = indx[k] + 1
        tmp[k] = decode_float(enc_line[lb:ub])
        lb = ub

    line = np.zeros((int(n_coords/2), 2))
    line[:, 0] = tmp[::2]
    line[:, 1] = tmp[1::2]

    return line

def convert_wgs1984_to_avo(gps_track, lon_col=0, inplace=False, is_easterly=True):
    '''
    '''

    if inplace:
        coords = gps_track
    else:
        coords = gps_track.copy()

    #Convert -E to +W
    if is_easterly:
        coords[:, lon_col] = -coords[:, lon_col]

    #Find new '-W' values and convert to +W + offset
    indx = coords[:, lon_col] < 0
    coords[indx, lon_col] = 360.0 + coords[indx, lon_col]

    return coords

def convert_avo_to_wgs1948(gps_track, lon_col=0, inplace=False):

    if inplace:
        coords = gps_track
    else:
        coords = gps_track.copy()

    #Convert +W to -E
    coords[:, lon_col] = -coords[:, lon_col]

    #Find -E < 180 and convert to +E
    indx = coords[:, lon_col] < -180.0
    coords[indx, lon_col] = 360.0 + coords[indx, lon_col]
    return coords

