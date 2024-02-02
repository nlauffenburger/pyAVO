
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


class Map():
    '''
    Class for plotting a map of data.
    '''
        
    def __init__(self, map_params):
        '''
        Method to initialize mapping parameters
        '''
        self.limits = (-179, -158, 53, 63)
        C = cm.get_cmap('gist_rainbow', 10)
        self.colorlist = C(np.arange(0,1,0.1).tolist())
        self.two_colorlist = [[0,  1,  0], [1, 0, 0]]
                                
        self.do_save = map_params['save']
        if map_params['save']:
            self.save_path = map_params['save_path']
    
    def draw_map(self, latitudes, longitudes, limits=None, labels=None, border=None, title=None, file_name=None, grids=None, legend=None):
        
        if not limits:
            limits = self.limits
        elif limits == 'find_limts':
            limits = (round(np.nanmin(longitudes), 0), round(np.nanmax(longitudes), 0), round(np.nanmin(latitudes), 0), round(np.nanmax(latitudes), 0))
        
        if not labels:
            labels = np.zeros(len(latitudes))
        
        cen_lon = np.mean(limits[0:2])
        cen_lat = np.mean(limits[2:4])
        
        ax = plt.axes(projection=ccrs.AlbersEqualArea(central_latitude=cen_lat, central_longitude=cen_lon))
        ax.set_extent(limits)
        ax.coastlines()
        ax.gridlines(draw_labels=True, linewidth=1, color='gray', alpha=0.2, linestyle='--')
        # Make sure it wraps around the first point
        border.append(border[0])
        if border is not None:
            plt.plot(np.transpose(border)[0], np.transpose(border)[1], color='black', linestyle='-', linewidth=2, transform=ccrs.Geodetic())
        
        # If there are just two labels, use more opposing colors:
        UL = np.unique(labels)
        UL = UL[np.logical_not(np.isnan(UL))]
        N = len(np.unique(labels))
        for l in UL:
            ind = np.argwhere(labels==l)
            if N==2:
                plt.plot(longitudes[ind], latitudes[ind], color=self.two_colorlist[int(l%len(self.two_colorlist))], marker='.', markersize=0.05, transform=ccrs.Geodetic(), label=l)
            else:
                plt.plot(longitudes[ind], latitudes[ind], color=self.colorlist[int(l%len(self.colorlist))], marker='.', markersize=0.05, transform=ccrs.Geodetic(), label=l)

        # Currently just plot all grids that are within the region if there is a border provided
        if grids is not None:
            for g in grids:
                if border is not None:
                    polygon = Polygon(border)
                    in_region = False
                    for p in g:
                        if polygon.contains(Point(p[0], p[1])):
                            in_region = True
                    if in_region:
                        bb_long = [g[0][0], g[1][0], g[2][0], g[3][0], g[0][0]]
                        bb_lat = [g[0][1], g[1][1], g[2][1], g[3][1], g[0][1]]
                        plt.plot(bb_long, bb_lat, color='grey', linestyle='-', linewidth=.5, transform=ccrs.Geodetic())
                else:
                    bb_long = [g[0][0], g[1][0], g[2][0], g[3][0], g[0][0]]
                    bb_lat = [g[0][1], g[1][1], g[2][1], g[3][1], g[0][1]]
                    plt.plot(bb_long, bb_lat, color='grey', linestyle='-', linewidth=.5, transform=ccrs.Geodetic())
        
        if legend is not None:
            plt.legend()
            
        # Labeling
        if title is not None:
            plt.title(title)
        
        if self.do_save:
            if not file_name:
                file_name = 'map'
            plt.savefig(self.save_path+file_name, dpi=1200)
        else:
            plt.show()

        plt.clf()
        
