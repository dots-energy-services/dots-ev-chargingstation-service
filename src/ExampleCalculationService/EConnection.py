# -*- coding: utf-8 -*-
from datetime import datetime
from esdl import esdl
import helics as h
import logging
from dots_infrastructure.DataClasses import EsdlId, HelicsCalculationInformation, PublicationDescription, SubscriptionDescription, TimeStepInformation
from dots_infrastructure.HelicsFederateHelpers import HelicsSimulationExecutor
from dots_infrastructure.Logger import LOGGER
from esdl import EnergySystem

import json

class CalculationServiceEV(HelicsSimulationExecutor):

    def __init__(self):
        super().__init__()

        publication_values = [
            PublicationDescription(global_flag=True, 
                                   esdl_type="EVChargingStation",
                                   output_name="state_of_charge_ev",
                                   output_unit="J",
                                   data_type=h.HelicsDataType.DOUBLE)
        ]

        evchargingstation_period_in_seconds = 900

        calculation_information = HelicsCalculationInformation(
            time_period_in_seconds=evchargingstation_period_in_seconds,
            offset=0, 
            uninterruptible=False, 
            wait_for_current_time_update=False, 
            terminate_on_error=True, 
            calculation_name="EConnectionDispatch", 
            inputs=[],
            outputs=publication_values, 
            calculation_function=self.send_state_of_charge
        )
        self.add_calculation(calculation_information)

        # publication_values = [
        #     PublicationDescription(True, "EConnection", "Schedule", "W", h.HelicsDataType.VECTOR)
        # ]
        #
        # e_connection_period_in_seconds = 21600
        #
        # calculation_information_schedule = HelicsCalculationInformation(e_connection_period_in_seconds, 0, False, False, True, "EConnectionSchedule", [], publication_values, self.e_connection_da_schedule)
        # self.add_calculation(calculation_information_schedule)

    def init_calculation_service(self, energy_system: esdl.EnergySystem):
        LOGGER.info("init calculation service: set-up initial state-of-charge")

        self.socs: dict[EsdlId, float]           = {}
        self.arrival_ptus: dict[esdl_id, list]   = {}
        self.departure_ptus: dict[esdl_id, list] = {}
        self.arrival_socs: dict[esdl_id, list]   = {}

        for esdl_id in self.simulator_configuration.esdl_ids:
            LOGGER.info(f"Example of iterating over esdl ids: {esdl_id}")

            # Get profiles from the ESDL
            for obj in energy_system.eAllContents():
                if hasattr(obj, "id") and obj.id == esdl_id:
                    esdl_object = obj

            description                  = json.loads(esdl_object.description)
            print(description)
            initial_soc                  = description['arrival_socs'][0] if description['arrival_ptus'][0] == 0 else 0.0
            self.socs[esdl_id]           = initial_soc
            self.arrival_ptus[esdl_id]   = description['arrival_ptus']
            self.departure_ptus[esdl_id] = description['departure_ptus']
            self.arrival_socs[esdl_id]   = description['arrival_socs']


    def send_state_of_charge(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):
        # START user calc
        LOGGER.info("calculation 'send_state_of_charge' started")
        LOGGER.info(f"Time: {simulation_time}")

        state_of_charge_ev_dict: dict[EsdlId, StateOfChargeEv] = {}

        # This sends out the soc at the beginning of the time step
        # That means, if the car arrives -> send arrival_soc
        # That means, if the car departed last time step -> send 0
        time_step_nr = time_step_number.current_time_step_number
        LOGGER.info(f"time_step_nr: {time_step_nr}")
        if (time_step_nr - 1) in self.arrival_ptus[esdl_id]:  # if time_step = 1, arrival_ptu is 0
            session_nr = self.arrival_ptus[esdl_id].index(time_step_nr - 1)
            state_of_charge_ev = self.arrival_socs[esdl_id][session_nr]
            self.socs[esdl_id] = state_of_charge_ev
        else:
            state_of_charge_ev = self.socs[esdl_id]

        LOGGER.debug(f"EV {esdl_id} sends: {state_of_charge_ev}")
        LOGGER.info("calculation 'send_state_of_charge' finished")
        # END user calc

        # return a list for all outputs:
        ret_val = {}
        ret_val["state_of_charge_ev"] = state_of_charge_ev
        print('state_of_charge_ev', state_of_charge_ev)
        # self.influx_connector.set_time_step_data_point(esdl_id, "EConnectionDispatch", simulation_time, ret_val["EConnectionDispatch"])
        return ret_val
    
    # def e_connection_da_schedule(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):
    #     ret_val = {}
    #     return ret_val

if __name__ == "__main__":

    helics_simulation_executor = CalculationServiceEV()
    helics_simulation_executor.start_simulation()
    helics_simulation_executor.stop_simulation()
