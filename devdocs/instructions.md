# Instructions for Flight Agent

## LLM analyzes user's input

### `resolve_airports.py` attain airports' IATA code from city name
`departing city` and `arrival city` must be specified.
- A city has only 1 airport, then return that IATA code
- A city/region has 2+ airports, then return a list `[iata1, iata2, ...]
- Ambiguous city, i.e., several cities with the same name, return a notice for user's further clarification
- Ambiguous city but one is more famous than others. Return the empirically default city. Like London in UK vs London in Canada.

