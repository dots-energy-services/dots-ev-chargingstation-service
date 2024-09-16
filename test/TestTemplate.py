from datetime import datetime
import unittest
from ExampleCalculationService.EConnection import CalculationServiceEConnection
from dots_infrastructure.DataClasses import SimulatorConfiguration, SimulaitonDataPoint, TimeStepInformation
from dots_infrastructure.test_infra.InfluxDBMock import InfluxDBMock
import helics as h

from dots_infrastructure import CalculationServiceHelperFunctions

BROKER_TEST_PORT = 23404
START_DATE_TIME = datetime(2024, 1, 1, 0, 0, 0)
SIMULATION_DURATION_IN_SECONDS = 960

def simulator_environment_e_connection():
    return SimulatorConfiguration("EConnection", ["f006d594-0743-4de5-a589-a6c2350898da"], "Mock-Econnection", "127.0.0.1", BROKER_TEST_PORT, "test-id", SIMULATION_DURATION_IN_SECONDS, START_DATE_TIME, "test-host", "test-port", "test-username", "test-password", "test-database-name", h.HelicsLogLevel.DEBUG, ["PVInstallation", "EConnection"])

class Test(unittest.TestCase):

    def setUp(self):
        CalculationServiceHelperFunctions.get_simulator_configuration_from_environment = simulator_environment_e_connection

    def test_example(self):
        # Arrange
        service = CalculationServiceEConnection()
        service.influx_connector = InfluxDBMock()
        pv_dispatch_params = {}
        pv_dispatch_params["PV_Dispatch"] = [1.0, 2.0]
        service.init_calculation_service(None)

        # Execute
        ret_val = service.e_connection_dispatch(pv_dispatch_params, datetime(2024,1,1), TimeStepInformation(1,2), "test-id", None)

        # Implement 
        self.assertEqual(ret_val["EConnectionDispatch"], 3.0)
        self.assertListEqual([SimulaitonDataPoint("EConnectionDispatch", datetime(2024,1,1), 3.0, "test-id")], service.influx_connector.data_points)

if __name__ == '__main__':
    unittest.main()
