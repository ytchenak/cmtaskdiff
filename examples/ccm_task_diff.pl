#!/bin/perl  -w

my $Version           = "1.1.1";

#----------------------------------------------
#
sub Usage()
{
    my ($Name) = ($0 =~ /([^\\\/]*).pl$/);
    my ($Space) = " " x length( $Name );

    print<<EOS;

$Name
  CCM (Synergy) Task Diff, version $Version.
  This script creates diff of CCM task (can be used latter for a patch)

  Syntax:
    $Name -t task_num
    --------------------------------------------------------------------
         $Space -t..................Task Number
         $Space -r..................Task repository to collect data
         $Space -d..................Get Diff
         $Space -l..................List of files
         $Space -i -n <number>......Show history of file number #
         $Space -p -n <number>......Patch file number #
         $Space -x -n <number>......Delete/Replace file number #
      ==================================================================
      Example:
        $Name -t 35048 -d ...... will create diff for this task
EOS
}


use strict;
use Data::Dumper;
use POSIX;
use Getopt::Long;
use Cwd qw(cwd);
use File::Basename;
use File::Path;
use Sys::Hostname;
use Carp;

##################################################
# Globals
##################################################
my $ccm = "ccm";
my $cwd          = dirname($0) eq '.' ? cwd() : dirname($0) ;
my $tasks_dir;
my $objects_file = "_objects.txt";
my $log_file = "log.txt";
my $is_simulate = 0;
my $is_trace = 0;
##################################################


sub IsWindows()
{
  return ($^O eq "MSWin32");
}


#----------------------------------------
#  Trace the message
#
sub trace($)
{
	my( $msg ) = (@_);
  chomp($msg);

  return  if !$is_trace;
  
	open ( my $OUTLOG, ">>$log_file" ) or croak ("Cannot open the log file $log_file");

  my ($package, $filename, $line, $subroutine) = caller(1);
  $subroutine =~ s/.*:://;

  my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
  #my $curTimeStr = sprintf("%02d-%02d-%04d %02d:%02d:%02d", $mon+1,$mday,$year+1900, $hour,$min,$sec);

  my $msgout = "$subroutine ($filename\:$line): $msg\n";

  
  print $OUTLOG $msgout;
	#print $msgout;
	close $OUTLOG;
}



#---------------------------------
# Execute one command
#
sub Execute($)
{
  my($cmd) = (@_);
  
  $cmd =~ s{\\}{/}g; #because UNC pathes

  trace( $cmd );
  my $out;
  if( !$is_simulate )
  {
    $out = `$cmd 2>&1`;
    my $errcode = $?;
    my $trace_out = "OUTPUT_BEGIN\n";
    $trace_out .= $out;
    $trace_out .= "\nOUTPUT_END\n";
    trace ( $trace_out );
    
  }
  return $out;
}


#############################
# get previous object for the current object
# use ccm diff -vc and find the prev. version in the following data
# Attribute name            ECSOrderForceGui.h#1       ECSOrderForceGui.h#2
# ECSOrderForceGui.h#2:incl:1
#
sub GetPrevObject($)
{
  my ($obj) = (@_);
  my $suffix = $obj;
  my ($ver, $type, $inst ) = split( ":", $obj );
  my $out = Execute("$ccm diff -vc  $obj");
  my ($ver_prev) = ( $out =~ /Associated tasks differs:\n\n(.*)/m );
  return undef if !defined($ver_prev);
  my $prev_obj = "$ver_prev:$type:$inst" ;
  return $prev_obj;
}


#############################
# get last object for the current object
# use ccm history and find the last version
#
sub GetLastObject($)
{
  my ($obj) = (@_);
  my $suffix = $obj;
  my ($ver, $type, $inst ) = split( ":", $obj );
  my $out = Execute("$ccm history $obj");
  my ($ver_last) = ( $out =~ /.*Object:\s+(\S+)/s );
  return undef if !defined($ver_last);
  my $prev_obj = "$ver_last:$type:$inst" ;
  return $prev_obj;
}

sub GetObjectPath($)
{
  my ($obj) = (@_);
  my $last_obj = GetLastObject($obj);
  return undef if !defined($last_obj);
  my $out = Execute("$ccm finduse $last_obj");
  my ($path) = ( $out =~ /(\S+)#[\d.\.]+@/s );
  return undef if !defined($path);
  return $path;
}

sub GetObjectFilename($)
{
  my ($obj) = (@_);

	my ($filename) = ( $obj =~ /(\S+)#/s );
  return $filename;
}

sub GetObjectContext($)
{
  my ($obj) = (@_);
  my $text = Execute("$ccm cat $obj");
  return $text;
}



sub FixPatchFileNames($$)
{
  my ($patch_text, $path) = (@_);

  $path = "undef" if !defined($path);

  my $head = sprintf "diff -u a/$path b/$path\n";
  $head .= sprintf "%s", "--- a/$path\n+++ b/$path\n";

  my $patch_fix = $patch_text;
  $patch_fix =~ s/.*\n.*\n/$head/m ;
  return $patch_fix;
}


#
sub MakePatchNew
{
	my ($obj_text, $path) = @_;
 
	my $patch_text = "diff -u a/$path b/$path\n";

	my $sign = "+";
	my $nlines = $obj_text =~ s/^/$sign/gm;

	# fake a diff with /dev/null
	my @range = ("0,0", "0,0");
	$range[1] = $nlines == 1 ? "1" : "1,$nlines";
	$patch_text .= "--- a/$path\n";
	$patch_text .= "+++ b/$path\n";
	$patch_text .= "\@\@ -$range[0] +$range[1] \@\@\n";
	$patch_text .= "$obj_text";
  return $patch_text;
}


sub SaveText($$)
{
  my ($fn, $text) = @_;
  open my $fh, ">$fn" or die "cannot open file $fn";
  print $fh $text;
  close $fn;
}


sub MakePatch($$$)
{
  my ($fn_prev, $fn_curr, $path) = @_; #filepath to files
  my $patch_text = Execute("diff -u $fn_prev $fn_curr");
  my $patch_fix = FixPatchFileNames($patch_text, $path);
  return $patch_fix;
}



############################################
sub DoDiff($)
############################################
{
	my ($task) = (@_);
	
  my $DEST="$tasks_dir/$task";

  rmtree $DEST;
  mkdir $DEST, 0777;
  mkdir "$DEST/old", 0777;
  mkdir "$DEST/new", 0777;
  my $objects_out = Execute("$ccm task $task -show objs -u");
  my @objects = split('\n', $objects_out );
  
  my $task_name = Execute("$ccm task -show synopsis $task");
  chomp @objects;
  open(my $report, ">$DEST/$objects_file") or die "cannot create report file $DEST/$objects_file, did you create $tasks_dir directory?\n";
  print $report "$task_name\n";
  print $report "Number\tObject\tPath\tNew/Changed\tDeleted\tAdded\n";

  my $object_report;
  my $number = 0;
  for my $object_curr (@objects) {
    $object_curr =~ s/^\s*(\S+).*/$1/;
    my $object_path = GetObjectPath($object_curr);
    my $text_curr = GetObjectContext( $object_curr );
    my $fn_curr = GetObjectFilename( "$object_curr" ) ;
    SaveText( "$DEST/new/$fn_curr", $text_curr  );

    my $fn_patch = GetObjectFilename( "$object_curr" ) ;
    $fn_patch .= ".patch";

    my $object_prev = GetPrevObject( $object_curr );
    if( defined( $object_prev ) )
    {
      my $text_curr = GetObjectContext( $object_prev );
      my $fn_prev = GetObjectFilename( "$object_prev" ) ;
      SaveText("$DEST/old/$fn_prev",  $text_curr );

      my $patch_text = MakePatch("$DEST/old/$fn_prev", "$DEST/new/$fn_curr", $object_path);

	    print "Patch of changed $object_curr goes into $DEST/$fn_patch\n";
      SaveText( "$DEST/$fn_patch", $patch_text );
      my $deleted =  $patch_text =~ s/(^\-[^\-])/$1/mg ;
      $deleted = 0 if $deleted eq "";
      my $added =  $patch_text =~ s/(^\+[^\+])/$1/mg ;
      $added = 0 if $added eq "";
      $object_path = "undef" if !defined($object_path);

			++$number;
      print $report "$number\t$object_curr\t$object_path\tChanged\t$deleted\t$added\n";
	  }
    else
    {
      my $patch_text = MakePatchNew( $text_curr, $object_path );
	    print "Patch of new $object_curr goes into $DEST/$fn_patch\n";
      SaveText( "$DEST/$fn_patch", $patch_text );
      print $report "$object_curr\t$object_path\tNew\t\t\n";
    }
  }
  close($report);

}



############################################
sub GetRecordsList($)
############################################
{
	my ($task) = (@_);

  my $DEST="$tasks_dir/$task";
  my @records;
	
  open(my $report, "<$DEST/$objects_file") or die "cannot open report file $DEST/$objects_file\n";
  my $head = 0;
  foreach my $line ( <$report> )
  {
  	chomp $line;
  	
  	if( $head == 0 )
  	{
	  	if( $line =~ /Number/ ) {
	  		$head = 1;
	  		next;
	  	}
	  	else
	  	{
	  		next;
	  	}
	  }
  	
  	my @fileds = (split '\s', $line);
  	my %record;
  	my $number = $fileds[0];
  	$record{number} 	= $fileds[0];
  	$record{object} 	= $fileds[1];
  	$record{name} 		= $fileds[2];
  	$records[ $number-1 ] = \%record;
  }
  
  close ($report);
	
	return @records;
}


############################################
sub GetRecordFromList($$)
############################################
{
	my ($task, $number) = (@_);
	my @records = GetRecordsList($task);
	my $record = $records[$number];
	return $record;
}


############################################
sub DoList($)
############################################
{
	my ($task) = (@_);

  my $DEST="$tasks_dir/$task";

	my @records = GetRecordsList($task);
	foreach my $record ( @records )
	{
		print "$$record{number}\t$$record{name}\n";
	}

}

  	

####################################################
sub DoHistory($$)
####################################################
{
	my ($task, $file_number) = (@_);
	my $task_dir = "$tasks_dir/$task";
	
	my $record = GetRecordFromList($task, $file_number);
	my $file_name = $$record{name};
	print "$file_name\n";
	my $out = Execute("$ccm history -g $file_name");
	print $out;
}

####################################################
sub DoDelete($$)
####################################################
{
	
	my ($task, $file_number) = (@_);
	my $task_dir = "$tasks_dir/$task";

 	my $answer = '?';
  do
  {
    print("\nDo you wish to continue?  (y / n)\n");
    $answer = <STDIN>;
    chomp($answer);
  }
  while( $answer ne 'y' && $answer ne 'n' );
  
  print("\nYour answer is \'$answer\'.");

  if( $answer eq 'n' )
  {
    exit(0);
  } 
  print "deleting...\n";
	
	my $record = GetRecordFromList($task, $file_number);
	my $file_name = $$record{name};
	print "$file_name\n";
	my $out = Execute("$ccm delete -replace $file_name");
	print $out;
	print "use to latest object\n";
	$out = Execute("$ccm use  /rules $file_name");
	print $out;
	
	
}


####################################################
sub DoPatch($$)
####################################################
{
	my ($task, $file_number) = (@_);
	my $task_dir = "$tasks_dir/$task";

	my $record = GetRecordFromList($task, $file_number);
	my $file_name = $$record{name};
	my $prev_obj 	= $$record{object};
	print "$file_name\n";
	
	
	my $out = '';
	$out = Execute("$ccm co  $file_name");
	print $out;
	
	#Associated object SimGraphI_AddToSim.cpp#3.1.1.1.3:cpp:1 with task 43956.
	my ($cur_obj) = ( $out =~ /Associated object (.*) with task/ );
	print "$cur_obj\n";
	if( !defined($cur_obj) )
	{
		print "cannot checkout\n";
		return;
	}
	
	$out = Execute("$ccm relate /name successor /from $prev_obj  /to $cur_obj");
	print $out;


	#TODO: ask
	unlink 	"$file_name.orig";
	unlink 	"$file_name.rej";
	
	
	my $short_name = $1 if( $file_name =~ /.*[\\\/](.*)/ );
	
	$out = Execute("patch -p1 -i $task_dir/$short_name.patch");
	print $out;
	
	$out = Execute("$ccm hist -g $file_name");

	if( -f "$file_name.rej" )
	{
		$out = `notepad.exe $file_name.rej`
	}
}



####################################################
sub main()
####################################################
{

  if ( @ARGV == 0 )
  {
      Usage();
      exit(1);
  }



  my $task = 0;
  my $help = 0;
  my $is_mode_diff = 0;
  my $is_mode_list = 0;
  my $is_mode_history = 0;
  my $is_mode_patch = 0;
  my $file_number = undef;
  my $is_mode_delete = 0;
  my $result = GetOptions(
    "t|task=i" => \$task,
    "r|tasks_dir=s" => \$tasks_dir,
    "d|diff" => \$is_mode_diff,
    "l|list" => \$is_mode_list,
    "i|history" => \$is_mode_history,
    "p|patch" => \$is_mode_patch,
    "x|delete" => \$is_mode_delete,
    "n|file_number=s" => \$file_number,
    "s|simulate" => \$is_simulate,
    "c|trace" => \$is_trace,


    
    "h|help" =>   \$help,
  );
  
  if ( !$result or $help == 1)
  {
      Usage();
      exit(1);
  }

  if ( !defined( $tasks_dir))
  {
  		if( IsWindows() ) 
  		{
  			$tasks_dir = "C:/Tasks";
  		}
  		else
  		{
  			$tasks_dir = "$ENV{HOME}/Tasks";
  		}
  }

  if ( !defined( $task))
  {
  	print "-t is missed\n";
  	exit(1);
  }


  my $task_dir="$tasks_dir/$task";


  ################################################
	# check the system
  ################################################

  my $diff_null = `diff 2>&1`;
  if( $? != 2 && $? != 512)
  {
    print "Error: diff is not found($?), it should be in PATH\n";
    exit 1;
  }

  my $ccm_test_out_null = `ccm delimiter 2>&1`;
  if( $? != 0)
  {
    print "Error: cannot connect to CCM: \n$ccm_test_out_null\nEnsure that ccm.exe in PATH and CCM engine is up\n";
    exit 1;
  }

  if ( ! -f $tasks_dir )
  {
  	mkdir $tasks_dir;
  	mkdir $tasks_dir, 0777;
  }
  
  if( defined($file_number) )
  {
  	--$file_number;
  }
  #print "using task repository: $tasks_dir\n";
  ################################################
  
  
  ################################################
  # start here
  ################################################
  if( $is_mode_diff == 1 )
  {
  	DoDiff($task);
  }
  elsif ($is_mode_list == 1)
  {
  	DoList($task);
  }
  elsif ($is_mode_history == 1)
  {
  	DoHistory($task, $file_number);
  }
  elsif ($is_mode_patch == 1)
  {
  	DoPatch($task, $file_number);
  }
  elsif ($is_mode_delete == 1)
  {
  	DoDelete($task, $file_number);
  }
  
  else
  {
  	print "no mode";
  }
  
}

&main();

