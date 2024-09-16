# -*- coding: utf-8 -*-
from datetime import datetime
from esdl import esdl
import helics as h
import logging
from dots_infrastructure.DataClasses import EsdlId, HelicsCalculationInformation, PublicationDescription, SubscriptionDescription, TimeStepInformation
from dots_infrastructure.HelicsFederateHelpers import HelicsSimulationExecutor
from dots_infrastructure.Logger import LOGGER
from esdl import EnergySystem

class CalculationServiceEConnection(HelicsSimulationExecutor):

    def __init__(self):
        super().__init__()

        subscriptions_values = [
            SubscriptionDescription(esdl_type="PVInstallation", 
                                    input_name="PV_Dispatch", 
                                    input_unit="W", 
                                    input_type=h.HelicsDataType.DOUBLE)
        ]

        publication_values = [
            PublicationDescription(global_flag=True, 
                                   esdl_type="EConnection", 
                                   output_name="EConnectionDispatch", 
                                   output_unit="W", 
                                   data_type=h.HelicsDataType.DOUBLE)
        ]

        e_connection_period_in_seconds = 60

        calculation_information = HelicsCalculationInformation(
            time_period_in_seconds=e_connection_period_in_seconds, 
            offset=0, 
            uninterruptible=False, 
            wait_for_current_time_update=False, 
            terminate_on_error=True, 
            calculation_name="EConnectionDispatch", 
            inputs=subscriptions_values, 
            outputs=publication_values, 
            calculation_function=self.e_connection_dispatch
        )
        self.add_calculation(calculation_information)

        publication_values = [
            PublicationDescription(True, "EConnection", "Schedule", "W", h.HelicsDataType.VECTOR)
        ]

        e_connection_period_in_seconds = 21600

        calculation_information_schedule = HelicsCalculationInformation(e_connection_period_in_seconds, 0, False, False, True, "EConnectionSchedule", [], publication_values, self.e_connection_da_schedule)
        self.add_calculation(calculation_information_schedule)

    def init_calculation_service(self, energy_system: esdl.EnergySystem):
        LOGGER.info("init calculation service")
        for esdl_id in self.simulator_configuration.esdl_ids:
            LOGGER.info(f"Example of iterating over esdl ids: {esdl_id}")

    def e_connection_dispatch(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):
        ret_val = {}
        ret_val["EConnectionDispatch"] = sum(param_dict["PV_Dispatch"])
        self.influx_connector.set_time_step_data_point(esdl_id, "EConnectionDispatch", simulation_time, ret_val["EConnectionDispatch"])
        return ret_val
    
    def e_connection_da_schedule(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):
        ret_val = {}
        return ret_val

if __name__ == "__main__":

    helics_simulation_executor = CalculationServiceEConnection()
    helics_simulation_executor.start_simulation()
    helics_simulation_executor.stop_simulation()
