# Developing Logs

### March 29 to be done
#### `search_flights.py`
- add more parameters including `type` `include_airline` `exclude_airline` `travel_class`
- save more information from the result. At least include `booking token`
- only develop one way mode currently. Return a notice if user want a round trip or multicity option.
- During test, stop after receive the parameters. Probably use more funtions. One to attain params, one to search, and one for filtering.

#### datasets and API non-alignment
`airports_iata.csv` use GB as country code for the UK, while serpapi accept both GB and UK


### March 31
#### SerpAPI test
- Need to include `max_stop` into `params`

#### Retrieve Booking Link Tool
- Need to add a new tool. After returning results to LLM, user may need to query again for the booking link.