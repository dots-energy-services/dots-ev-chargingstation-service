# -*- coding: utf-8 -*-
from datetime import datetime
from esdl import esdl
import helics as h
from dots_infrastructure.DataClasses import EsdlId, HelicsCalculationInformation, PublicationDescription, SubscriptionDescription, TimeStepInformation
from dots_infrastructure.HelicsFederateHelpers import HelicsSimulationExecutor
from dots_infrastructure.Logger import LOGGER
from esdl import EnergySystem
from dots_infrastructure.CalculationServiceHelperFunctions import get_single_param_with_name

import json
import math

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
        self.ev_period_in_seconds = 900

        calculation_information = HelicsCalculationInformation(
            time_period_in_seconds=evchargingstation_period_in_seconds,
            offset=0, 
            uninterruptible=False, 
            wait_for_current_time_update=False, 
            terminate_on_error=True, 
            calculation_name="send_state_of_charge",
            inputs=[],
            outputs=publication_values, 
            calculation_function=self.send_state_of_charge
        )
        self.add_calculation(calculation_information)

        subscriptions_values = [
            SubscriptionDescription(esdl_type="EConnection",
                                input_name="dispatch_ev",
                                input_unit="W",
                                input_type=h.HelicsDataType.DOUBLE)
            ]

        evchargingstation_update_period_in_seconds = 900

        calculation_information_update = HelicsCalculationInformation(
            time_period_in_seconds=evchargingstation_update_period_in_seconds,
            offset=0,
            uninterruptible=False,
            wait_for_current_time_update=False,
            terminate_on_error=True,
            calculation_name="update_state_of_charge",
            inputs=subscriptions_values,
            outputs=[],
            calculation_function=self.update_state_of_charge
        )

        self.add_calculation(calculation_information_update)

    def init_calculation_service(self, energy_system: esdl.EnergySystem):
        LOGGER.info("init calculation service: set-up initial state-of-charge")

        self.socs: dict[EsdlId, float]            = {}
        self.arrival_ptus: dict[EsdlId, list]    = {}
        self.departure_ptus: dict[EsdlId, list]  = {}
        self.arrival_socs: dict[EsdlId, list]    = {}
        self.max_charge_rate: dict[EsdlId, float] = {}
        self.capacity: dict[EsdlId, float]        = {}
        self.efficiency: dict[EsdlId, float]      = {}

        for esdl_id in self.simulator_configuration.esdl_ids:

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
            # Charging parameters
            self.max_charge_rate[esdl_id] = esdl_object.power
            self.capacity[esdl_id] = description['max_soc']
            self.efficiency[esdl_id] = description['efficiency']



    def send_state_of_charge(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):
        # START user calc
        LOGGER.info(f"Time: {simulation_time}")

        # This sends out the soc at the beginning of the time step
        # That means, if the car arrives -> send arrival_soc
        # That means, if the car departed last time step -> send 0
        time_step_nr = time_step_number.current_time_step_number
        LOGGER.info(f"time_step_nr: {time_step_nr}")
        if (time_step_nr - 1) in self.arrival_ptus[esdl_id]:
            session_nr = self.arrival_ptus[esdl_id].index(time_step_nr - 1)
            state_of_charge_ev = self.arrival_socs[esdl_id][session_nr]
            self.socs[esdl_id] = state_of_charge_ev
        else:
            state_of_charge_ev = self.socs[esdl_id]

        LOGGER.debug(f"EV {esdl_id} sends: {state_of_charge_ev}")
        # END user calc

        # return a list for all outputs:
        ret_val = {}
        ret_val["state_of_charge_ev"] = state_of_charge_ev

        return ret_val
    
    def update_state_of_charge(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):
        # This function takes place at the end of the time step, after the EMS did its calculation

        LOGGER.info(f"Time: {simulation_time}")
        # Get input
        active_power_to_charge = get_single_param_with_name(param_dict, "dispatch_ev")

        # Get parameters
        max_charge_rate = self.max_charge_rate[esdl_id]
        capacity = self.capacity[esdl_id]

        # Check if charging power does not exceed the maximum value
        LOGGER.info(f"To charge: {active_power_to_charge}/{max_charge_rate}")
        eps = 0.001
        if (active_power_to_charge >= max_charge_rate) and (abs(active_power_to_charge - max_charge_rate) < eps):
            active_power_to_charge = max_charge_rate

        if active_power_to_charge > max_charge_rate:
            raise ValueError(f"EV {esdl_id} is charging more than its max power")

        # Update state of charge (preparing for the next time step)
        # The soc calculated here is the soc at the end of the time step
        # That means that we simply update the soc here, and handle soc updates at arrival/departure in send_soc
        LOGGER.info(f"SoC before of EV {esdl_id}: {self.socs[esdl_id]}")
        self.socs[esdl_id] += active_power_to_charge * self.ev_period_in_seconds

        LOGGER.info(f"SoC after of EV {esdl_id}: {self.socs[esdl_id]}")

        # Correct small exceedances
        if math.ceil(self.socs[esdl_id]) == 0:
            self.socs[esdl_id] = 0.0
        if (self.socs[esdl_id] > capacity) and (math.floor(self.socs[esdl_id]) <= capacity):
            self.socs[esdl_id] = capacity

        # Check if the state of charge is within bounds
        if (math.ceil(self.socs[esdl_id])) < 0 or (self.socs[esdl_id] > capacity):
            raise ValueError(f"EV {esdl_id} is charged over/under its capacity")

        return {}

if __name__ == "__main__":

    helics_simulation_executor = CalculationServiceEV()
    helics_simulation_executor.start_simulation()
    helics_simulation_executor.stop_simulation()
