# mswyw - Microservice: Worth Your Weight?

## What it is

A little utility that gathers some metrics about your deployed services and computes 1 metric - mswyw. 
It quantifies if your [microservice](https://en.wikipedia.org/wiki/Microservices) is worth its weight. The formula is simple:

mswyw = VALUE / COST

Examples of *VALUE* attributes:

* Number of endpoints (presumably the more endpoints, the more functionality, the more useful. Controversial)
* Number of [Use Case Points](https://en.wikipedia.org/wiki/Use_Case_Points) it implements (a measure of features/value to the user)
* Number of [Function Points](https://en.wikipedia.org/wiki/Function_point) it implements (a measure of features/value to the user)
* APDEX - a measure of user satisfaction with the performance of your (micro)service
* Error Rate - a measure of user lack of satisfaction with your service
* Requests per minute (rpm) - the more your service can take, the leaner it is to run.
  
Examples of *COST* attributes:

* Total amount of RAM used by all replicas of your (micro)service. You know that Amazon charges for that, right? The
  less memory you need, the cheaper the machine instance you can get away with.
* Amount of CPU percentage used by each of your replicas. You also pay for CPU. A smaller machine with 
  optimized/faster code will cost you less.



## Motivation

Use and abuse of microservices is intense lately. I have seen my fair share of convoluted, bloated Dockerfiles, 
not to mention REST microservices that eat 300MB RAM and with one single endpoint, which tells if a person's 
document ID is well formed. You know, the kind of thing you do with 20 lines of code. This kind of utility is 
much better suited for a reusable library. If it is to be shared by many projects... sure, go ahead and make it 
into a separate git repo and produce a binary JAR (if in Java) which people can import. It does *not* need to 
be a microservice.

I agree with Bob Martin that one should be able to [defer the deploy decision](https://blog.cleancoder.com/uncle-bob/2014/10/01/CleanMicroserviceArchitecture.html).
I should be able to deploy code  with a REST façade of 20 endpoints or as 2 services each with a REST façade of 10 
endpoints each. Or with a SOAP façade. Or both. Or GraphQL. You get the idea - don't hardcode the façade technology 
into your reusable core. Read about [clean architectures](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html), for example.

By obtaning a metric we hope to let people compare the "fat factor" of their (micro)services.

## How to install

Make sure your Python has paver installed (pip3 install paver) and then run:
```
pip3 install git+https://github.com/sglebs/mswyw
```


## How to run

You need to tell mswyw how to gather runtime information (RAM, APDEX etc) by informing the name of a provider, 
in the form of a fully qualified name of a Python module that implements the API we need.
If, instead, the value you provide is a literal json, we will use that instead. If the value is a valid file path, 
we assume it is a json file with the values we need.

You also need the same for info about the code (lines of code, language, etc). The same applies here about the value 
being either a fully qualified name of a module or a literal json or a json file.

Currently the only runtimeProvider supported is New Relic (nrelic, the default by the way) but we also plan to add Elastic APM support.

Example:

`
mswyw --runtimeProvider=nrelic 
      --codeInfoProvider={"loc":120,"lang":"java"} 
      --providerParams={"nrelic.APPID":"123456","nrelic.APIKEY":"ABCDEFG"}
`

You can also get consolidated results for a collection of apps by name (regex) if you prefer:
`
mswyw --runtimeProvider=nrelic 
      --codeInfoProvider={"loc":120,"lang":"java"} 
      --providerParams={"nrelic.APPS":"foo.*bar$","nrelic.APIKEY":"ABCDEFG"}
`


## Special Thanks

We would like to thank [Softplan](http://www.softplan.com.br) for supporting the development of this utility.  


