#!/usr/bin/env node

/*

Demetris Roumis Dec052016. Based from Jeremy Magland.
Updated AKGillespie Aug2018 to longer include datasets, pipelines, or curation script

---changing datasets dirstruct to organize by tetrode/epoch instead of epoch/tetrode
---allows for use of the ms_multi or ms2 pipeline that concatenates epochs from single tetrodes

Use this to set up a day's worth of analysis at L. Frank's lab.

Suppose the day's data are located at /data/path
For example, the following would already exist for
animal : JZ1
date : 20161205
epochs : 4,5
tetrodes : 1,2

JZ1/preprocessing/20161205/20161205_JZ1_04.mda/20161205_JZ1_nt1.mda
JZ1/preprocessing/20161205/20161205_JZ1_04.mda/20161205_JZ1_nt2.mda
JZ1/preprocessing/20161205/20161205_JZ1_05.mda/20161205_JZ1_nt1.mda
JZ1/preprocessing/20161205/20161205_JZ1_05.mda/20161205_JZ1_nt2.mda
...
and we'd want it to create the following:
JZ1/preprocessing/20161205/20161205_JZ1.mountain/nt1/4/raw.mda.prv
JZ1/preprocessing/20161205/20161205_JZ1.mountain/nt1/5/raw.mda.prv
JZ1/preprocessing/20161205/20161205_JZ1.mountain/nt2/4/raw.mda.prv
JZ1/preprocessing/20161205/20161205_JZ1.mountain/nt2/5/raw.mda.prv
...

Step 1: cd to ~/mountainlab/devtools/franklab/
run >>./setup_mountainsort_franklab_multi_NTlinks.node.js </data/path>
where /data/path is the absolute path to the .mountain directory for that animal, date

Step 2: cd /data/path and do the sorting

*/

var fs=require('fs');
var exec = require('child_process').exec;

function usage() {
	console.log('Usage: ./setup_mountainsort.node.js [directory name]');
}

//command-line parameters
var CLP=new CLParams(process.argv);
//var directory=CLP.unnamedParameters[0];//bug preventing CL arg parsing?
var CLargs=process.argv; 
var directory = CLargs[2];
if (!directory) {
	usage();
	process.exit(-1);
}

//var top_list=fs.readdirSync('.'); //should use dir CLP, not cwd
var top_list=fs.readdirSync(directory);
var mda_directories=[];
for (var i in top_list) {
	if (string_ends_with(top_list[i],'.mnt')) {
		mda_directories.push(top_list[i]);
	}
}

var datasets='';
//var pipelines='ms franklab_001.pipeline'+'\n'+'ms_multi mountainsort_002_multisession.pipeline --curation=curation.script'+'\n'+'ms2 ms2_002.pipeline --curation=curation_ms2.script --mask_out_artifacts=true';
var dsnames = {}; //intitialize set of tetrode names
for (var dd in mda_directories) {
	var input_directory=directory+mda_directories[dd];
	var date=get_date_from_directory_name(mda_directories[dd]);
	var animal = get_animal_from_directory_name(mda_directories[dd]);
	var epoch=get_epoch_from_directory_name(input_directory);
//	epoch = parseInt(epoch).toString(); // strip any zero padding
	var output_directory_mountain=directory + '/' + date+'_'+animal+'.mountain';  
	var list=fs.readdirSync(input_directory);
	var raw_fnames=[];
	console.log(date, animal)
	mkdir_if_needed(output_directory_mountain); // make date_animal.mountain dir
//	pipelines+=' --sessions='+epoch; // append current epoch string to pipeline session(epoch) list

	var dsname=input_directory.slice(0,input_directory.length-4);
	dsname=dsname.slice(dsname.lastIndexOf('.')+1); // grab tetrode string from mda file > 'dsname'
	output_directory_tet = output_directory_mountain+'/'+dsname; // for each <tet>.mda create a <tetdatasetprv> dir in parent dir
	mkdir_if_needed(output_directory_tet);
	var params0={samplerate:30000};
	var exe='ml-prv-create';
	var args=[input_directory+'/',output_directory_tet+'/raw.mda.prv'];
	fs.writeFileSync(output_directory_tet+'/params.json',JSON.stringify(params0));
	if (!(dsname in dsnames)){ //if a dataset.txt entry has not yet been created for this tetrode
		datasets+=dsname+' '+dsname+'\n';// append tetrode to datasets.txt
		}
	dsnames[dsname]=true; //append tetrode name to set of tetrode names
	console.log(exe, args)
	run_process_and_read_stdout(exe,args,function(txt) {
		console.log(txt);
		});
}

function get_date_from_directory_name(str) { 
	return str.split('.')[0].split('_')[0];
}

function get_animal_from_directory_name(str) {
	return str.split('.')[0].split('_')[1];
}

function get_epoch_from_directory_name(str) {
	return str.split('.')[0].split('_')[2];
}

function CLParams(argv) {
	this.unnamedParameters=[];
	this.namedParameters={};

	var args=argv.slice(2);
	for (var i=0; i<args.length; i++) {
		var arg0=args[i];
		if (arg0.indexOf('--')===0) {
			arg0=arg0.slice(2);
			var ind=arg0.indexOf('=');
			if (ind>=0) {
				this.namedParameters[arg0.slice(0,ind)]=arg0.slice(ind+1);
			}
			else {
				this.namedParameters[arg0]=args[i+1]||'';
				i++;
			}
		}
		else if (arg0.indexOf('-')===0) {
			arg0=arg0.slice(1);
			this.namedParameters[arg0]='';
		}
		else {
			this.unnamedParameters.push(arg0);
		}
	}
}

function mkdir_if_needed(path) {
	var fs=require('fs');
	if (!fs.existsSync(path)){
    	fs.mkdirSync(path);
	}
}

function string_ends_with(str,str2) {
	if (str2.length>str.length) return false;
	return (str.slice(str.length-str2.length)==str2);
}

function string_contains(str,str2) {
	var ind=str.indexOf(str2);
	return (ind>=0);
}

function run_process_and_read_stdout(exe,args,callback) {
	console.log ('RUNNING:'+exe+' '+args.join(' '));
	var P=require('child_process').spawn(exe,args);
	var txt='';
	P.stdout.on('data',function(chunk) {
		txt+=chunk;
	});
	P.on('close',function(code) {
		callback(txt);
	});
}

