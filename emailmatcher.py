import csv
from sys import argv
import logging
import Levenshtein
import usaddress

logging.basicConfig(filename='matches.log', filemode='a', encoding='utf-8', 
                    level=logging.INFO)

script, msg_file = argv

def search(nameFromEmail, listofALFs):
    return [element for element in listofALFs 
            if element['ALFnameDB'] == nameFromEmail]
    
def lev_search(nameFromEmail, listofALFs):
    return [(Levenshtein.ratio(nameFromEmail,element['ALFnameDB']), element)
           for element in listofALFs]

def cleanCityStateZip(city, state, zipcode):
# usaddress only separates the zip-plus 4 if there's a space, not a -
    justzip = zipcode.split('-')[0]
    return [item.strip().rstrip(',').upper() 
        for item in (city, state, justzip)]

#not Windows-1252
email = open(msg_file,encoding='utf-16-le', errors='ignore').read()

try: 
    custOrg = email.index("Customer Organization Name:\t ")
    end = email.index("After we receive your approval,")
except: 
    raise Exception(f"Wasn't able to find the text in the email "
                    f"for initial approval requests.")
requestInfo = email[custOrg:end-5]

start = requestInfo.index("Facility ID\t \n")
facility = requestInfo[start+14:]

for emailALF in facility.split('\t \n'):
    emailALFName, emailALFAddress, emailExternalFacilityID = emailALF.split('\t ')
    emailALFAddress = usaddress.parse(emailALFAddress)
    emailALFAddress = [tuple(reversed(t)) for t in emailALFAddress]
    emailALFAddressDict = dict()
    
    for k, v in emailALFAddress:
        emailALFAddressDict.setdefault(k, []).append(v)
    emailALFAddressDict = {
        k: " ".join(v) for k, v in emailALFAddressDict.items()}
    emailCityStateZip = cleanCityStateZip(
        emailALFAddressDict['PlaceName'], emailALFAddressDict['StateName'], 
        emailALFAddressDict['ZipCode'])
    
    logging.info('------------------------------\n' + 'Date of request: ' 
        + requestInfo.split("\t ")[17])
    logging.info('Customer Organization Name: ' + requestInfo.split("\t ")[1])
    logging.info('Facilities Requested: ' + emailALFName)
    
    #csv should have columns facilityID,facilityalias,ALFCode,ALFnameDB,
    #Address1,City,State,Zip,Zip2
    with open('DBexportofALFs.csv', mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        try:
            result = search(emailALFName, csv_reader)
            logging.info(f"{result[0].get('ALFnameDB')} is an ALF at "
                f"{result[0].get('facilityalias')} that is a "
                f"perfect match on name...")
            dbCityStateZip = cleanCityStateZip(
                result[0].get('City'), result[0].get('State'), 
                result[0].get('Zip'))
            
            if emailCityStateZip == dbCityStateZip \
                    and emailALFAddressDict['AddressNumber'] \
                    in result[0].get('Address1') \
                    and emailALFAddressDict['StreetName'] \
                    in result[0].get('Address1'):
                logging.info(f"...and the street address looks like a match "
                    f"too.\nemail address = "
                    f"{' '.join(emailALFAddressDict.values())}"
                    f"\ndatabase address "
                    f"= {result[0].get('Address1')} "
                    f"{result[0].get('City')} "
                    f"{result[0].get('State')} "
                    f"{result[0].get('Zip')} "
                    f"{result[0].get('Zip2')}")
            else: 
                logging.info(f"not a perfect match = why? "
                    f"email vs. database says {emailCityStateZip} "
                    f"{dbCityStateZip} "
                    f"{emailALFAddressDict['AddressNumber']} "
                    f"{result[0].get('Address1')} "
                    f"{emailALFAddressDict['StreetName']} "
                    f"{result[0].get('Address1')} "
                    f"email address = {emailALFAddressDict} "
                    f"database address = {result[0]}")
            if len(result) > 1:
                logging.info(f"however there's also an ALF of that exact name "
                             f"at other integrated facilties too")
        except IndexError:
            csv_file.seek(0)
            logging.info('There were no perfect matches on name.')
            scores = lev_search(emailALFName, csv_reader)
            #https://sparkbyexamples.com/python/sort-list-of-tuples-in-python/
            #specify key to prevent sort from moving on to the second element
            #in the tuple for same scores 
            #since the second element is a dict and can't be sorted
            scores.sort(key=lambda x: x[0],reverse=True)
            top3 = scores[:3]

            logging.info(f'Top 3 best imperfect matches to '
                f'{emailALFName} are:')
            for count, winner in enumerate(top3):
                logging.info(f"---#{count + 1}---{winner[1]['ALFnameDB']}, "
                             f"an ALF at {winner[1]['facilityalias']}")
                dbCityStateZip = cleanCityStateZip(
                    winner[1]['City'], winner[1]['State'], winner[1]['Zip'])
                if emailCityStateZip == dbCityStateZip \
                        and emailALFAddressDict['AddressNumber'] \
                        in winner[1]['Address1'] \
                        and emailALFAddressDict['StreetName'] \
                        in winner[1]['Address1']:
                    logging.info(f"...and the street address looks like a "
                        f"match too.\nemail address = "
                        f"{' '.join(emailALFAddressDict.values())} \ndatabase "
                        f"address = {winner[1].get('Address1')} "
                        f"{winner[1].get('City')} {winner[1].get('State')} "
                        f"{winner[1].get('Zip')} {winner[1].get('Zip2')}")
                else: 
                    logging.info(f"But the address is not a great match. "
                        f"why? email vs. database says {emailCityStateZip} "
                        f"{dbCityStateZip}")