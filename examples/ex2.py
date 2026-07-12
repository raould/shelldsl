import shelldsl as _

fetch = _.cmd("curl -s https://world.openfoodfacts.org/api/v0/product/737628064502.json").json()
print(fetch)
