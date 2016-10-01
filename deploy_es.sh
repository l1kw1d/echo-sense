APPCFG=~/google_appengine/appcfg.py # Customize based on local setup

rollback(){
	echo -e "\nRolling back.....\n"
    if [ "$s_length" -gt 1 ]; then
        com="python $APPCFG rollback --oauth2 $(dirname $0)/app.yaml $services"
    else
        com="python $APPCFG rollback --oauth2 $(dirname $0)"
    fi
    eval $com

}

check_server_tests(){
	./run_tests.sh
	RESULT=$?
	if [ $RESULT -ne 0 ]; then
		echo -e "\nSERVER UNIT TESTS FAILED!\n"
		cancel_deploy
	fi
}

install_npm_dependencies(){
    echo "Updating npm dependencies according to the package.json..."
    npm install .
	RESULT=$?
	if [ $RESULT -ne 0 ]; then
		echo -e "\nUPDATING NPM DEPENDENCIES FAILED!\n"
		cancel_deploy
	fi
}

check_js_tests(){
	npm test
	RESULT=$?
	if [ $RESULT -ne 0 ]; then
		echo -e "\nJEST UNIT TESTS FAILED!\n"
		cancel_deploy
	fi
}

check_indexes(){
	indexes_diff=$(git diff index.yaml)
	if [[ -n $indexes_diff ]]; then
		echo
		echo "$indexes_diff"
		echo
		echo -e "\nUNCOMMITED INDEXES FOUND!\n"
		cancel_deploy
	fi
}

deploy(){
	if [ "$1" = "rollback" ]; then
		rollback
	fi
	check_services
	check_indexes
	check_server_tests
	check_js_tests
	install_npm_dependencies
	gulp production
    if [ "$s_length" -gt 1 ]; then
        python $APPCFG update $services
    else
    	for s in $services; do
    		python $APPCFG update $s
    	done
    fi
}

cancel_deploy(){
	echo -e "\nExitted without updating $version!\n"
	exit 1
}

check_services() {
    for a in $services; do
            service_version_line=$(grep "^version:" $(dirname $0)/"$a");
            service_version=${service_version_line##* };
            if [ "$service_version" != "$version" ]; then
                    echo "";
                    echo "ALERT !! service {$a} version {$service_version} did not match default version {$version}";
                    cancel_deploy
            fi
    done
}

services="app.yaml processing.yaml"
# first do a git pull to bring down tags
git pull
version_line=$(grep "^version:" $(dirname $0)/app.yaml);
version=${version_line##* };
# production versions only contain digits, hf and - (dash)
production_version=false
# note: keep in sync with constants.PROD_VERSION_REGEX
if [[ $version =~ ^[0-9hf\-]+[a-z]?$ ]]; then
	production_version=true
	env="production"
	# if deploying to production, it is compulsory to deploy all services
	services="app.yaml processing.yaml"
else
	env="staging"
fi

s_length=$(echo $services | wc -c)
if [ "$s_length" -gt 1 ]; then
   prom="Are you sure you want to deploy to $version with services $services? (y/n) "
else
   prom="Are you sure you want to deploy to $version? (y/n) "
fi

read -p "$prom" -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
	#production versions only contain digits, hf and - (dash)
	if [[ $version =~ ^[0-9hf\-]+$ ]]; then
		read -p "This looks like a production version ($version), Are you really sure? (y/n) " -n 1 -r
		echo
		if [[ $REPLY =~ ^[Yy]$ ]]; then
			# if no tag yet create it, then push tags
			git tag -a -m "New production version by $(whoami) on $(date)" "v$version"
			git push --tags
			# deploy production version
			deploy
			echo -e "\n\nDeploy to production Successful!\n"
		else
			cancel_deploy
		fi
	else
		#deploy non-production version
		deploy
	fi
else
	cancel_deploy
fi
