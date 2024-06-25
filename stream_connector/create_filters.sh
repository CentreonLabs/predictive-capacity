#!/bin/bash

Help(){
   # Display Help
   echo "Add description of the script functions here."
   echo
   echo "Syntax: scriptTemplate [-H|M|S|h]"
   echo "options:"
   echo "H     filter metrics by this host_name regex"
   echo "S     filter metrics by this service_description regex"
   echo "M     filter metrics by this metric_name regex"
   echo "h     Print this Help."
   echo
}

add_metric(){
	host_id=$1
	service_id=$2
	host_name=$3
	service_description=$4
	metric_name=$5
	min=$6
	max=$7
	warn=$8
	warn_low=$9
	crit=$10
	crit_low=$11

	echo "{"
	echo "\"host_id\":$host_id,"
	echo "\"service_id\":$service_id,"
	echo "\"name\":\"$metric_name\","
	echo "\"bounds\":["
	if [ "$min" != "NULL" ]; then echo "\"min\",";fi
	if [ "$max" != "NULL" ]; then echo "\"max\",";fi
	if [ "$warn" != "NULL" ]; then echo "\"warning\",";fi
	if [ "$crit" != "NULL" ]; then echo "\"critical\",";fi
	if [ "$warn_low" != "NULL" ]; then echo "\"warn_low\",";fi
	if [ "$crit_low" != "NULL" ]; then echo "\"crit_low\",";fi
	echo "]"
	echo "},"
}

while getopts "hH:S:M:" option;do
	case $option in
		h) # display Help
			Help
			exit;;
		H) 
			host_name_regex=$OPTARG;;
		S) 
			service_description_regex=$OPTARG;;
		M) 
			metric_name_regex=$OPTARG;;
      \?)
         echo "Error: Invalid option"
         exit;;
   esac
done

# Set the database host, user, and password
DB_HOST="127.0.0.1"
# DB_USER="user"
# DB_PASS="password"

# Set the database name and table
DB_NAME="centreon_storage"

k=0
filter_string=""
if [ ! -z "$host_name_regex" ] || [ ! -z "$metric_name_regex" ] || [ ! -z "$service_description_regex" ]; then
	filter_string="$filter_string where "

	if [ ! -z "$host_name_regex" ];then
		filter_string="$filter_string id.host_name regexp '$host_name_regex'"
		k=$((k+1))
	fi

	if [ ! -z "$metric_name_regex" ];then
		if [ $k -gt 0 ];then
			filter_string="$filter_string and m.metric_name regexp '$metric_name_regex'"
		else
			filter_string="$filter_string m.metric_name regexp '$metric_name_regex'"
		fi
		k=$((k+1))
	fi

	if [ ! -z "$service_description_regex" ];then
		if [ $k -gt 0 ]; then
			filter_string="$filter_string and id.service_description regexp '$service_description_regex'"
		else
			filter_string="$filter_string id.service_description regexp '$service_description_regex'"
		fi
	fi
fi

# Set the query to make
QUERY="SELECT id.host_id, id.service_id, id.host_name, id.service_description, m.metric_name, m.min, m.max, m.warn, m.warn_low, m.crit, m.crit_low 
       FROM metrics AS m INNER JOIN index_data AS id ON (m.index_id = id.id) $filter_string
       order by id.service_id, m.metric_name;"

echo sql query
echo $QUERY
echo 

# Make the query and store the result in a variable
RESULT=$(mysql -h $DB_HOST $DB_NAME -e "$QUERY")

# Save the JSON to a file
echo "$RESULT" > result.tsv

# Format result in json
echo "{\"schema\": {" > /etc/centreon-broker/filters.json
echo "\"version\": \"1.0.0\"," >> /etc/centreon-broker/filters.json
echo "\"name\": \"centreon-collector\"" >> /etc/centreon-broker/filters.json
echo "}," >> /etc/centreon-broker/filters.json
echo "\"metrics\":[" >> /etc/centreon-broker/filters.json
while IFS="	" read -r host_id service_id host_name service_description metric_name min max warn warn_low crit crit_low
do
	add_metric $host_id $service_id $host_name $service_description $metric_name $min $max $warn $warn_low $crit $crit_low
done < <(tail -n +2 result.tsv) >> /etc/centreon-broker/filters.json
echo "]}" >> /etc/centreon-broker/filters.json

rm result.tsv

echo file saved as /etc/centreon-broker/filters.json
