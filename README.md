
# Calculation service for esdl_type EVChargingStation:

This calculation service maintains the state of charge of an EV charging station.

## Calculations

### send state of charge 

Sends the current state of charge of the EV charging station.
#### Output values
|Name             |data_type             |unit             |description             |
|-----------------|----------------------|-----------------|------------------------|
|state_of_charge_ev|DOUBLE|W|The state of charge of the EV charging station.|
### update state of charge 

Updates the state of charge of the EV charging station based upon the amount of power dispatched from the energy management system.
#### Input parameters
|Name            |esdl_type            |data_type            |unit            |description            |
|----------------|---------------------|---------------------|----------------|-----------------------|
|dispatch_ev|EConnection|DOUBLE|W|The amount of power dispatched to the EV charging station.|

### Relevant links
|Link             |description             |
|-----------------|------------------------|
|[EVChargingStation](https://energytransition.github.io/#router/doc-content/687474703a2f2f7777772e746e6f2e6e6c2f6573646c/EVChargingStation.html)|Details on the EVChargingStation esdl type|
