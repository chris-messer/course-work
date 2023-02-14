import simpy
import random
import pandas as pd

# Now we need to define our environment. We are wanting to simulate an
# airport, so we will define a class of Airport. If you are new to python,
# a class is helpful when we are wanting to be able to save state changes of
# an object. In this example, we want to have one airport that has
# attributes about it that change over time but are consistent.

# We will also allow the airport to take in some arguments, for things like
# arrival rate, check rate, etc. Most of these are defined by the question
# in the homework. Some of them we will just have to make a guess for the
# sake of our model. In real life we would collect data from an airport and
# use that as our variable values, but for now we will just make a guess. I
# will annotate my code as I go.

class Airport:
    # call the init method - this means as soon as we actually create an
    # airport in our code, it will do all of the things in the init section.
    # Here we will assign it some things an airport will need to have. It
    # will ne need to know things like do I have scanners? How many? How
    # fast are people arriving at me? etc.
    def __init__(self, env, arrRate, checkRate,
                 numCheckers, numScanners, runTime, minScan, maxScan):
        self.env = env
        self.arrRate = arrRate
        self.checkRate = checkRate
        self.numCheckers = numCheckers
        self.numScanners = numScanners
        self.runTime = runTime
        self.minScan = minScan
        self.maxScan = maxScan
        # here we will give it some empty variables to store information in
        # later.
        self.passengerCount = 0
        self.checkCount = 0
        self.arrivals = 0
        self.passenger_list = []

        # And now we actually create those resources we talked about earlier!
        self.checker = simpy.Resource(env, self.numCheckers)
        # since the scanners all have a queue, and the passengers will be
        # looking for the scanner with the shortest line, lets store all of
        # our scanners in a list
        self.scanners = []
        for i in range(self.numScanners):
            self.scanners.append(simpy.Resource(env, 1))

    # Now lets give our resources some actions. Here we are telling the
    # check function in needs to wait according to an exponential
    # distribution, of 1/checkout rate. This is just how the python package
    # interprets it a poisson distribution of a lambda value.

    def check(self, passenger):
        yield self.env.timeout(random.expovariate(1.0 / self.checkRate))
        # random.expovariate(1.0 / self.checkRate)

    # and now we do the same for scanning time, except this time it takes in
    # a normal distribution.
    def scan(self, passenger):
        yield self.env.timeout(random.uniform(self.minScan, self.maxScan))


# Great! now we do the same for passengers. We will create a passenger
# object so it can store information. Esssentially, once the passenger gets
# through the checking and scanning lines, we will ask each one how long it
# took them to get through, by calling the passenger.checkTime attribute.
class Passenger:
    # give the passengers some attributes
    def __init__(self, name, airport):
        self.airport = airport
        self.name = name

        self.arrTime = self.airport.env.now
        self.checkTime = None
        self.airport.env.process(self._get_boarding_pass_checked())
        # print(f'Boarding check took {self.checkTime} for passenger {
        # self.name}')

    # now we have to tell the passenger what to do.
    def _get_boarding_pass_checked(self):
        with self.airport.checker.request() as request:
            tIn = self.airport.env.now  # first record when the passenger
            # starts to get checked
            yield request  # now request a checker, and don't do anything
            # until they get one.
            yield self.airport.env.process(self.airport.check(self.name))
            #now that they found a checker, get checked
            tOut = self.airport.env.now  # record when passenger ends being
            # checked
            self.checkTime = (tOut - tIn)  # find total time for passenger
            # to be checked
            self.airport.checkCount += 1  # record in our airport object
            # that someone has been checked
            self.airport.env.process(self._get_scanned())  # call the
            # scanning process to start

    # this is just a function to help our passenger find the shortest line.
    def _find_shortest_scanner_line(self):
        min_queue = 0
        for i in range(1, self.airport.numScanners):
            if len(self.airport.scanners[i].queue) < len(
                    self.airport.scanners[min_queue].queue):
                min_queue = i
        return min_queue

    # I won't annotate line by line, but this is the same process as the
    # checking process.
    def _get_scanned(self):
        shortest_line = self._find_shortest_scanner_line()
        with self.airport.scanners[shortest_line].request() as request:
            tIn = self.airport.env.now
            yield request
            yield self.airport.env.process(self.airport.scan(self.name))
            tOut = self.airport.env.now
            self.departTime = tOut
            self.scanTime = (tOut - tIn)
            self.totalTime = (self.departTime - self.arrTime)
            self.airport.passengerCount += 1
            self.airport.passenger_list.append(self)
            # print(f'Passenger {self.name} waited {self.scanTime}')


# Now that we have our objects created, we have to open our airport for
# business!

# create a function that opens our airport. We will instruct it on how fast
# passengers arrive, etc.
def open_airport(env,
                 airport,
                 passenger=1):
    p_list = []
    airport.passenger_list.append(Passenger(passenger, airport))

    while True:
        yield env.timeout(random.expovariate(airport.arrRate))
        passenger += 1
        airport.arrivals += 1
        Passenger(passenger, airport)


# Think of this as the manager of the airport function. Someone has to
# actually open the doors-that is what the .run function does at the bottom
# there.
def run_sim(arrRate=5,
            checkRate=.75,
            numCheckers=1,
            numScanners=1,
            runTime=720,
            minScan=.5,
            maxScan=1.5):
    env = simpy.Environment()
    airport = Airport(env,
                      arrRate=arrRate,
                      checkRate=checkRate,
                      numCheckers=numCheckers,
                      numScanners=numScanners,
                      runTime=runTime,
                      minScan=minScan,
                      maxScan=maxScan)

    env.process(open_airport(env, airport))
    env.run(until=100)
    return airport

# Now we want to open the airport for several days to really get a feel for
# what the average times are. So we replicate it 10 times
def replicate(replications, arrRate=5, numCheckers=1, numScanners=1):
    average_time = []
    for i in range(replications):
        airport = run_sim(arrRate=arrRate,
                          numCheckers=numCheckers,
                          numScanners=numScanners)
        wait_times = [p.totalTime for p in airport.passenger_list]
        average = sum(wait_times) / len(wait_times)
        average_time.append(average)
    return sum(average_time) / len(average_time)

# Now, we want to see how varying the number of checkers and scanners
# actually affects the wait times of customers. So we will loop over that as
# well
def simSlow():
    df = []
    for numScanners in range(1, 31):
        for numCheckers in range(1, 31):
            average_time = replicate(1,
                                     arrRate=5,
                                     numCheckers=numCheckers,
                                     numScanners=numScanners)
            speed = {'numScanners': numScanners,
                     'numCheckers': numCheckers,
                     'wait_time': average_time}
            df.append(speed)
            #print(speed)
    return pd.DataFrame(df)

#Now do the same for a busy airport by increasing the lambda value to 50
def simBusy():
    df = []
    for numScanners in range(1, 51):
        for numCheckers in range(1, 51):
            average_time = replicate(1,
                                     arrRate=50,
                                     numCheckers=numCheckers,
                                     numScanners=numScanners)
            speed = {'numScanners': numScanners,
                     'numCheckers': numCheckers,
                     'wait_time': average_time}
            df.append(speed)
            #print(speed)
    return pd.DataFrame(df)

#finally, save the results to a csv file.
slow = simSlow()
slow.to_csv('slow.csv', index=False)
fast = simBusy()
fast.to_csv('fast.csv', index=False)
print('done')