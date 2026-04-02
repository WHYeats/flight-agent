#### data dictionary to save all flights data `_flight_store: dict[str, dict] = {}`
```python
_flight_store = {
  "date1": {
    "min price": min_price_of_the_day,
    "created at": an_exact_time,
    "flights": [
      {
      "flights": [
        {
          "departure_airport": {
            "name": "Dalian Zhoushuizi International Airport",
            "id": "DLC",
            "time": "2026-06-30 10:30"
          },
          "arrival_airport": {
            "name": "Incheon International Airport",
            "id": "ICN",
            "time": "2026-06-30 12:45"
          },
          "duration": 75,
          "airplane": "Airbus A330",
          "airline": "Asiana Airlines",
          "airline_logo": "https://www.gstatic.com/flights/airline_logos/70px/OZ.png",
          "travel_class": "Economy",
          "flight_number": "OZ 302",
          "legroom": "31 in",
          "extensions": [
            "Average legroom (31 in)",
            "In-seat power outlet",
            "On-demand video",
            "Carbon emissions estimate: 66 kg"
          ]
        },
        {
          "departure_airport": {
            "name": "Incheon International Airport",
            "id": "ICN",
            "time": "2026-06-30 21:20"
          },
          "arrival_airport": {
            "name": "Los Angeles International Airport",
            "id": "LAX",
            "time": "2026-06-30 16:50"
          },
          "duration": 690,
          "airplane": "Airbus A380",
          "airline": "Asiana Airlines",
          "airline_logo": "https://www.gstatic.com/flights/airline_logos/70px/OZ.png",
          "travel_class": "Economy",
          "flight_number": "OZ 204",
          "legroom": "33 in",
          "extensions": [
            "Above average legroom (33 in)",
            "In-seat power & USB outlets",
            "On-demand video",
            "Carbon emissions estimate: 745 kg"
          ],
          "overnight": true,
          "often_delayed_by_over_30_min": true
        }
      ],
      "layovers": [
        {
          "duration": 515,
          "name": "Incheon International Airport",
          "id": "ICN"
        }
      ],
      "total_duration": 1280,
      "carbon_emissions": {
        "this_flight": 812000,
        "typical_for_this_route": 601000,
        "difference_percent": 35
      },
      "price": 789,
      "type": "One way",
      "airline_logo": "https://www.gstatic.com/flights/airline_logos/70px/OZ.png",
      "booking_token": "WyJDalJJTUV4TFZ6aERkRXgyVW5kQlFYRk1lbEZDUnkwdExTMHRMUzB0TFhSaWFIZ3hOa0ZCUVVGQlIyNU5ZMmRWVG14TmRWTkJFZ3RQV2pNd01ueFBXakl3TkJvTENLZm9CQkFDR2dOVlUwUTRISENuNkFRPSIsW1siRExDIiwiMjAyNi0wNi0zMCIsIklDTiIsbnVsbCwiT1oiLCIzMDIiXSxbIklDTiIsIjIwMjYtMDYtMzAiLCJMQVgiLG51bGwsIk9aIiwiMjA0Il1dXQ==",
      "tags": ["some_notice_strings"]
    },
    ]
  }
  "date2": {
    "min_price": xxx,
    "flights": [
      {
        ...
      }
    ]
  }
}
```

#### distilled data before sending to LLM
For a single day search or detailed information: `flight_results`
```python
flight_results = [
  {
    "id" = 1,
    "airline": "xxx",
    "price": 789,
    "flights": "OZ302, OZ204",
    "schedule": "10:30-12:45, 21:20-16:50",
    "transit": "1 stop at Seoul",
    "tags": ["best choice","least price"]
  }，
  {
    "id" = 2,
    ...
  }
]
```

For multiple days search: `days_results`
Each day contains a best flight of that day.
```python
days_results = {
  "date1":{
      "id" = 1,
      "airline": "xxx",
      "price": 789,
      "flights": "OZ302, OZ204",
      "schedule": "10:30-12:45, 21:20-16:50",
      "transit": "1 stop at Seoul",
      "tags": ["best choice","least price"]
  },
  "date2":{
      "id" = 2,
      "airline": "xxx",
      "price": 980,
      "flights": "OZ302, OZ204",
      "schedule": "10:30-12:45, 21:20-16:50",
      "transit": "1 stop at Seoul",
      "tags": ["best choice","least price"]
  },
  ...
}
```

### token maps
token maps for days results:
```python
token_map = {
  "date1": "token of the best flight in date1",
  "date2": "token of the best flight in date2",
  ...
}
```

token maps for single day multiple flights:
```python
token_map = {
  "id1": "token of flight id1",
  "id2": "token of flight id2",
  ...
}