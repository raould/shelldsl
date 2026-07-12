import shelldsl as _
import vm_sdk

fetch = _.cmd("curl -s https://world.openfoodfacts.org/api/v0/product/737628064502.json").json()
vm_sdk.prnt(fetch)
