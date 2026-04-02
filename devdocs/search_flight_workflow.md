## Search_flight_workflow Pseudo code
```python
def search_flight_workflow(date_from: str, date_to: str = "", buffer_days: int = 0, other_params):
  dates = _date_expand()  # returns a list of dates, if single day, then len(dates) = 1

  tasks = [async_search_single_day(d, other_params) for d in dates]
  all_raw_results = await asyncio.gather(*tasks)
  
  for date, result in zip(dates, all_raw_results):
    _flight_store[date] = filtering(result)


  if multiple days:
    days_result = distill_days()
    token_map = distill_days_token_map()
    return days_result
  else # single day
    flights_result = distill_flights_in_a_day()
    token_maps = distill_flights_token_map()
    return flights_result

```