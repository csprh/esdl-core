import os
import shutil
from datetime import datetime
from unittest import TestCase

import numpy as np

from esdl import CubeConfig, Cube
from esdl.cube_provider import CubeSourceProvider

CUBE_DIR = 'testcube'


class CubeTest(TestCase):
    def setUp(self):
        while os.path.exists(CUBE_DIR):
            shutil.rmtree(CUBE_DIR, False)

    def tearDown(self):
        # while os.path.exists(CUBE_DIR):
        #     shutil.rmtree(CUBE_DIR, True)
        pass

    def test_update(self):
        cube = Cube.create(CUBE_DIR, CubeConfig())
        self.assertTrue(os.path.exists(CUBE_DIR))
        self.assertTrue(os.path.exists(CUBE_DIR + '/CHANGELOG'))

        provider = CubeSourceProviderMock(cube.config, start_time=datetime(2001, 1, 1), end_time=datetime(2001, 2, 1))
        cube.update(provider)

        self.assertEqual([(datetime(2001, 1, 1, 0, 0), datetime(2001, 1, 9, 0, 0)),
                          (datetime(2001, 1, 9, 0, 0), datetime(2001, 1, 17, 0, 0)),
                          (datetime(2001, 1, 17, 0, 0), datetime(2001, 1, 25, 0, 0)),
                          (datetime(2001, 1, 25, 0, 0), datetime(2001, 2, 2, 0, 0))],
                         provider.trace)

        self.assertTrue(os.path.exists(CUBE_DIR + "/cube.config"))
        self.assertTrue(os.path.exists(CUBE_DIR + "/data/LAI/2001_LAI.nc"))
        self.assertTrue(os.path.exists(CUBE_DIR + "/data/FAPAR/2001_FAPAR.nc"))

        cube.close()

        with self.assertRaises(IOError):
            cube.update(provider)

        cube2 = Cube.open(CUBE_DIR)
        self.assertEqual(cube.config.spatial_res, cube2.config.spatial_res)
        self.assertEqual(cube.config.temporal_res, cube2.config.temporal_res)
        self.assertEqual(cube.config.file_format, cube2.config.file_format)
        self.assertEqual(cube.config.compression, cube2.config.compression)

        provider = CubeSourceProviderMock(cube2.config,
                                          start_time=datetime(2006, 12, 15),
                                          end_time=datetime(2007, 1, 15))
        cube2.update(provider)
        self.assertEqual([(datetime(2006, 12, 11, 0, 0), datetime(2006, 12, 19, 0, 0)),  # 8 days
                          (datetime(2006, 12, 19, 0, 0), datetime(2006, 12, 27, 0, 0)),  # 8 days
                          (datetime(2006, 12, 27, 0, 0), datetime(2007, 1, 1, 0, 0)),  # 8 days
                          (datetime(2007, 1, 1, 0, 0), datetime(2007, 1, 9, 0, 0)),  # 8 days
                          (datetime(2007, 1, 9, 0, 0), datetime(2007, 1, 17, 0, 0))],  # 8 days
                         provider.trace)

        self.assertTrue(os.path.exists(CUBE_DIR + "/data/LAI/2006_LAI.nc"))
        self.assertTrue(os.path.exists(CUBE_DIR + "/data/LAI/2007_LAI.nc"))
        self.assertTrue(os.path.exists(CUBE_DIR + "/data/FAPAR/2006_FAPAR.nc"))
        self.assertTrue(os.path.exists(CUBE_DIR + "/data/FAPAR/2007_FAPAR.nc"))
        from xarray import Variable
        try:
            data = cube2.data
            self.assertIsNotNone(data)
            self.assertEqual((2, 11 * 46, 720, 1440), data.shape)
            self.assertEquals(['FAPAR', 'LAI'], data.variable_names)

            lai_var = data.variable('LAI')
            self.assert_cf_conformant_time_info(data, 'LAI')
            self.assert_cf_conformant_geospatial_info(data, 'LAI')
            self.assertIsNotNone(lai_var)
            self.assertIs(lai_var, data['LAI'])
            self.assertIs(lai_var, data[1])
            self.assertIsInstance(lai_var, Variable)
            self.assertIs(data.variable(1), data[1])
            array = lai_var[:, :, :]
            self.assertEqual(array.shape, (138, 720, 1440))
            scalar = lai_var[3, 320, 720]
            self.assertEqual(scalar.values, np.array(0.14, dtype=np.float32))

            fapar_var = data.variable('FAPAR')
            self.assert_cf_conformant_time_info(data, 'FAPAR')
            self.assert_cf_conformant_geospatial_info(data, 'FAPAR')
            self.assertIsNotNone(fapar_var)
            self.assertIs(fapar_var, data['FAPAR'])
            self.assertIs(fapar_var, data[0])
            self.assertIs(data.variable(0), data[0])
            array = fapar_var[:, :, :]
            self.assertEqual(array.shape, (138, 720, 1440))
            scalar = fapar_var[3, 320, 720]
            self.assertEqual(scalar.values, np.array(0.62, dtype=np.float32))

            result = data.get('FAPAR',
                              [datetime(2001, 1, 1), datetime(2001, 2, 1)],
                              [-90, 90],
                              [-180, +180])
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].shape, (4, 720, 1440))

            result = data.get(['FAPAR', 'LAI'],
                              [datetime(2001, 1, 1), datetime(2001, 2, 1)],
                              [50.0, 60.0],
                              [10.0, 30.0])
            self.assertEqual(2, len(result))
            self.assertEqual(result[0].shape, (4, 40, 80))
            self.assertEqual(result[1].shape, (4, 40, 80))

            result, = data.get(1,
                               datetime(2001, 1, 20),
                               0,
                               0)
            self.assertEqual(result.shape, ())
            self.assertEqual(result.values, np.array(0.13, dtype=np.float32))

            result, = data.get(0,
                               datetime(2001, 1, 20),
                               -12.6,
                               5.9)
            self.assertEqual(result.shape, ())
            self.assertEqual(result, np.array(0.615, dtype=np.float32))

            result = data.get((1, 0),
                              datetime(2001, 1, 20),
                              53.4,
                              13.1)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0].shape, ())
            self.assertEqual(result[1].shape, ())
            self.assertEqual(result[0].values, np.array(0.13, dtype=np.float32))
            self.assertEqual(result[1].values, np.array(0.615, dtype=np.float32))
        finally:
            cube2.close()

    def assert_cf_conformant_time_info(self, data, var_name):
        P = 8.  # period = 8d
        L = 138  # num periods

        ds = data.dataset(var_name)

        self.assertIn('time', ds.variables)
        time_var = ds.variables['time']
        self.assertEqual(time_var.attrs['long_name'], 'time')
        self.assertEqual(time_var.attrs['standard_name'], 'time')
        self.assertEqual(time_var.attrs['bounds'], 'time_bnds')
        # self.assertEqual(time_var.attrs['calendar'], 'gregorian')
        # self.assertEqual(time_var.attrs['units'], 'days since 2001-01-01 00:00')
        self.assertEqual(time_var.shape, (L,))
        # for i in range(L):
        #    print(i, i / P, time_var[i])
        self.assertEqual(time_var.values[0], np.datetime64('2001-01-05T01:00:00.000000000+0100'))
        self.assertEqual(time_var.values[46], np.datetime64('2006-01-05T01:00:00.000000000+0100'))
        self.assertIn('time_bnds', ds.variables)
        time_bnds_var = ds.variables['time_bnds']
        # self.assertEqual(time_bnds_var.calendar, 'gregorian')
        # self.assertEqual(time_bnds_var.units, 'days since 2001-01-01 00:00')
        self.assertEqual(time_bnds_var.shape, (L, 2), )
        self.assertEqual(time_bnds_var.values[0, 0], np.datetime64('2001-01-01T01:00:00.000000000+0100'))
        self.assertEqual(time_bnds_var.values[0, 1], np.datetime64('2001-01-09T01:00:00.000000000+0100'))

    def assert_cf_conformant_geospatial_info(self, data, var_name):
        W = 1440  # width in lon
        H = 720  # height in lat

        RES = 360.0 / W
        RES05 = 0.5 * RES

        ds = data.dataset(var_name)

        self.assertIn('lat', ds.variables)
        lat_var = ds.variables['lat']
        self.assertEqual(lat_var.attrs['long_name'], 'latitude')
        self.assertEqual(lat_var.attrs['standard_name'], 'latitude')
        self.assertEqual(lat_var.attrs['units'], 'degrees_north')
        self.assertEqual(lat_var.attrs['bounds'], 'lat_bnds')
        self.assertEqual((H,), lat_var.shape)
        self.assertEqual(+90. - RES05, lat_var[0])
        self.assertEqual(-90. + RES05, lat_var[H - 1])

        self.assertIn('lon', ds.variables)
        lon_var = ds.variables['lon']
        self.assertEqual(lon_var.attrs['long_name'], 'longitude')
        self.assertEqual(lon_var.attrs['standard_name'], 'longitude')
        self.assertEqual(lon_var.attrs['units'], 'degrees_east')
        self.assertEqual(lon_var.attrs['bounds'], 'lon_bnds')
        self.assertEqual((W,), lon_var.shape)
        self.assertEqual(-180. + RES05, lon_var.values[0])
        self.assertEqual(+180. - RES05, lon_var.values[W - 1])

        self.assertIn('lat_bnds', ds.variables)
        lat_bnds_var = ds.variables['lat_bnds']
        self.assertEqual(lat_bnds_var.attrs['units'], 'degrees_north')
        self.assertEqual((H, 2), lat_bnds_var.shape)
        self.assertEqual(+90. - RES, lat_bnds_var.values[0, 0])
        self.assertEqual(+90., lat_bnds_var.values[0, 1])
        self.assertEqual(-90., lat_bnds_var.values[H - 1, 0])
        self.assertEqual(-90. + RES, lat_bnds_var.values[H - 1, 1])

        self.assertIn('lon_bnds', ds.variables)
        lon_bnds = ds.variables['lon_bnds']
        self.assertEqual(lon_bnds.attrs['units'], 'degrees_east')
        self.assertEqual((W, 2), lon_bnds.shape)
        self.assertEqual(-180., lon_bnds[0, 0])
        self.assertEqual(-180. + RES, lon_bnds.values[0, 1])
        self.assertEqual(+180. - RES, lon_bnds.values[W - 1, 0])
        self.assertEqual(+180., lon_bnds.values[W - 1, 1])


class CubeSourceProviderMock(CubeSourceProvider):
    def __init__(self,
                 cube_config,
                 start_time=datetime(2013, 1, 1),
                 end_time=datetime(2013, 2, 1)):
        super(CubeSourceProviderMock, self).__init__(cube_config, 'test')
        self.start_time = start_time
        self.end_time = end_time
        self.trace = []
        self.lai_value = 0.1
        self.fapar_value = 0.6

    def prepare(self):
        pass

    @property
    def temporal_coverage(self):
        return self.start_time, self.end_time

    @property
    def spatial_coverage(self):
        return 0, 0, self.cube_config.grid_width, self.cube_config.grid_height

    @property
    def variable_descriptors(self):
        return {
            'LAI': {
                'data_type': np.float32,
                'fill_value': 0.0,
                'scale_factor': 1.0,
                'add_offset': 0.0,
            },
            'FAPAR': {
                'data_type': np.float32,
                'fill_value': -9999.0,
                'units': '1',
                'long_name': 'FAPAR'
            }
        }

    def compute_variable_images(self, period_start, period_end):
        self.trace.append((period_start, period_end))
        self.lai_value += 0.01
        self.fapar_value += 0.005
        image_width = self.cube_config.grid_width
        image_height = self.cube_config.grid_height
        image_shape = (image_height, image_width)
        return {'LAI': np.full(image_shape, self.lai_value, dtype=np.float32),
                'FAPAR': np.full(image_shape, self.fapar_value, dtype=np.float32)}

    def close(self):
        pass
