from datetime import datetime
import unittest
from evservice.evservice import CalculationServiceEV
from dots_infrastructure.DataClasses import SimulatorConfiguration, TimeStepInformation
from dots_infrastructure.test_infra.InfluxDBMock import InfluxDBMock
import helics as h
from esdl.esdl_handler import EnergySystemHandler

from dots_infrastructure import CalculationServiceHelperFunctions

BROKER_TEST_PORT = 23404
START_DATE_TIME = datetime(2024, 1, 1, 0, 0, 0)
SIMULATION_DURATION_IN_SECONDS = 960

def simulator_environment_e_connection():
    return SimulatorConfiguration("EConnection", ["e19a105b-97cb-4e3e-8767-67a9764b77f6"], "Mock-Econnection", "127.0.0.1", BROKER_TEST_PORT, "test-id", SIMULATION_DURATION_IN_SECONDS, START_DATE_TIME, "test-host", "test-port", "test-username", "test-password", "test-database-name", h.HelicsLogLevel.DEBUG, ["PVInstallation", "EConnection"])

class Test(unittest.TestCase):

    def setUp(self):
        CalculationServiceHelperFunctions.get_simulator_configuration_from_environment = simulator_environment_e_connection
        esh = EnergySystemHandler()
        esh.load_file('test.esdl')
        energy_system = esh.get_energy_system()
        self.energy_system = energy_system

    def test_send_state_of_charge(self):

        # Arrange
        service = CalculationServiceEV()
        service.influx_connector = InfluxDBMock()

        # Initialize calculation functions
        service.init_calculation_service(self.energy_system)

        # Execute
        ret_val_soc_not_present = service.send_state_of_charge(None, datetime(2020,9,1,12,0), TimeStepInformation(1,2), "e19a105b-97cb-4e3e-8767-67a9764b77f6", self.energy_system)
        ret_val_soc_present = service.send_state_of_charge(None, datetime(2020,9,1,12,0), TimeStepInformation(75,80), "e19a105b-97cb-4e3e-8767-67a9764b77f6", self.energy_system)

        # Assert
        self.assertEqual(ret_val_soc_not_present["state_of_charge_ev"], 0.0)
        self.assertEqual(ret_val_soc_present["state_of_charge_ev"], 179197200)

    def test_update_state_of_charge(self):

        # Arrange
        id_to_test = "e19a105b-97cb-4e3e-8767-67a9764b77f6"
        service = CalculationServiceEV()
        service.influx_connector = InfluxDBMock()

        # Initialize calculation functions
        service.init_calculation_service(self.energy_system)

        # Execute
        param_dict = {}
        param_dict["dispatch_ev"] = 50.0
        service.update_state_of_charge(param_dict, datetime(2020,9,1,12,0), TimeStepInformation(1,2), id_to_test, self.energy_system)

        # Assert
        self.assertEqual(service.socs[id_to_test], 50.0 * 900)

    def test_update_state_of_charge_charging_beyond_maximum_power(self):

        # Arrange
        id_to_test = "e19a105b-97cb-4e3e-8767-67a9764b77f6"
        service = CalculationServiceEV()
        service.influx_connector = InfluxDBMock()

        # Initialize calculation functions
        service.init_calculation_service(self.energy_system)

        # Execute and assert
        param_dict = {}
        param_dict["dispatch_ev"] = 12000.0
        with self.assertRaises(ValueError):
            service.update_state_of_charge(param_dict, datetime(2020,9,1,12,0), TimeStepInformation(1,2), id_to_test, self.energy_system)

    def test_update_state_of_charge_overcharging_gives_error(self):

        # Arrange
        id_to_test = "e19a105b-97cb-4e3e-8767-67a9764b77f6"
        service = CalculationServiceEV()
        service.influx_connector = InfluxDBMock()

        # Initialize calculation functions
        service.init_calculation_service(self.energy_system)

        # Execute and assert
        param_dict = {}
        param_dict["dispatch_ev"] = 11000.0
        
        service.update_state_of_charge(param_dict, datetime(2020,9,1,12,0), TimeStepInformation(75,80), id_to_test, self.energy_system)
        service.update_state_of_charge(param_dict, datetime(2020,9,1,12,0), TimeStepInformation(76,80), id_to_test, self.energy_system)
        service.update_state_of_charge(param_dict, datetime(2020,9,1,12,0), TimeStepInformation(77,80), id_to_test, self.energy_system)
        with self.assertRaises(ValueError):
            service.update_state_of_charge(param_dict, datetime(2020,9,1,12,0), TimeStepInformation(78,80), id_to_test, self.energy_system)

if __name__ == '__main__':
    unittest.main()
