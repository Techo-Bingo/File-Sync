#!/usr/bin/expect -f
################################################################
set timeout 30
################################################
#Define variable in shell                      #
################################################
set SSH_EXP_INF "\033\[1;31mINFO>\033\[0m"
set SSH_EXP_ERR "\033\[1;31mERROR>\033\[0m"
set SSH_RSA_PUB "$env(HOME)/.ssh/id_rsa.pub"
set SSH_EXP_LNK ""
set SSH_EXP_USR ""
set SSH_EXP_PWD ""
set SSH_EXP_HST ""
################################################
#-----------------------------------------------
#check parameters valid
#-----------------------------------------------
proc fun_ssh_chk_parm {ssh_tmp_link} {
 set ssh_tmp_cnct "${ssh_tmp_link}";
 set ssh_tmp_user "";
 set ssh_tmp_host "";
 set ssh_tmp_pswd "";
 set ssh_ats_indx -1;
 set ssh_xxs_indx -1;
 #---------------
 set ssh_ats_indx [string last  "@" "${ssh_tmp_cnct}"];
 set ssh_xxs_indx [string first "/" "${ssh_tmp_cnct}"];
 if { "${ssh_ats_indx}"!="-1"  } {
  if { "${ssh_xxs_indx}"!="-1"  } {
   set ssh_tmp_user [string range "${ssh_tmp_cnct}" 0                           [expr ${ssh_xxs_indx} - 1 ]  ];
   set ssh_tmp_host [string range "${ssh_tmp_cnct}" [expr ${ssh_ats_indx} + 1 ] end                          ];
   set ssh_tmp_pswd [string range "${ssh_tmp_cnct}" [expr ${ssh_xxs_indx} + 1 ] [expr ${ssh_ats_indx} - 1 ]  ];
   if { "${ssh_tmp_host}"=="" } {
    fun_ssh_out_eror "";
   } else {
    if { "${ssh_tmp_pswd}"=="" } {
     fun_ssh_out_eror "";
    } else {
     if { "${ssh_tmp_user}"=="" } {
      fun_ssh_out_eror "";
     } else {
      set ::SSH_EXP_USR "${ssh_tmp_user}"
      set ::SSH_EXP_HST "${ssh_tmp_host}"
      set ::SSH_EXP_PWD "${ssh_tmp_pswd}"
      set ::SSH_EXP_LNK "${ssh_tmp_link}"
     }
    }
   }
  } else {
   fun_ssh_out_eror "";
  }
 } else {
  fun_ssh_out_eror "";
 }
}
#-----------------------------------------------
#check SSH_RSA_PUB file
#-----------------------------------------------
proc fun_ssh_chk_file {} {
    if { ![file exists ${::SSH_RSA_PUB}] } {
  if {[catch { spawn ssh-keygen -t rsa } error]} {
   fun_ssh_out_eror "${error}"
  }
  expect -nocase -re "\(.*\):"
  send -- "\r"
  expect -nocase -re "passphrase.*:"
  send -- "\r"
  expect -nocase -re "passphrase.*again:"
  send -- "\r"
  expect eof
    }
}
#-----------------------------------------------
#make ssh link with remote host
#-----------------------------------------------
proc fun_ssh_mak_link {} {
 set ssh_pass_mark 0;
 set ssh_cycl_done 0;
 set ssh_pass_info "SUCCESS";
 while { !${ssh_cycl_done} } {
     spawn ssh -o KbdInteractiveDevices=no ${::SSH_EXP_USR}@${::SSH_EXP_HST} "echo ${ssh_pass_info}";
     expect {
   -nocase -re "yes/no" {
    set ssh_pass_mark 1;
    send -- "yes\r";
    set ssh_cycl_done 1;
   }
   -nocase -re "password: " {
    set ssh_cycl_done 1;
   }
   "${ssh_pass_info}" {
    exit 0;
   }
   "@@@@@@@@@@@@@@@@@@@@" {
    expect eof;
    fun_ssh_rst_host ${::SSH_EXP_HST};
   }
   eof {
    fun_ssh_out_eror "";
   }
   timeout {
    fun_ssh_out_eror "Timeout";
   }
     }
 }
 if {${ssh_pass_mark}} {
     expect {
   ${ssh_pass_info} {
       exit 0;
   }
   -nocase -re "password: " {}
     }
 }
 send -- "${::SSH_EXP_PWD}\r";
 expect {
     -nocase "try again" {
   fun_ssh_out_eror "Password error";
     }
     -nocase "password:" {
   fun_ssh_out_eror "Password error";
     }
     -nocase "Received disconnect from" {
   fun_ssh_out_eror "Received disconnect from remote host";
     }
     ${ssh_pass_info} {}
 }
 expect eof;
 if {[catch {
     set ssh_rsa_pub [open ${::SSH_RSA_PUB} RDONLY];
     set ssh_pub_key [read ${ssh_rsa_pub}];
     close ${ssh_rsa_pub};
 } error]} {
     fun_ssh_out_eror "${error}";
 }
 set ssh_pub_key [string trimright ${ssh_pub_key} "\r\n"]
 spawn ssh -o KbdInteractiveDevices=no ${::SSH_EXP_USR}@${::SSH_EXP_HST} "cd;chmod 755 ./;mkdir -p .ssh > /dev/null 2>&1;chmod 700 .ssh/;echo \"${ssh_pub_key}\" >>.ssh/authorized_keys;chmod 644 .ssh/authorized_keys;sudo /opt/UBP/bin/pam_tally2.sh -r;"
 expect -nocase -re "password:"
  send -- "${::SSH_EXP_PWD}\r"
 expect eof
}
#-----------------------------------------------
#print error and exit with code (1)
#-----------------------------------------------
proc fun_ssh_rst_host {SSH_EXP_HST} {
    set ssh_tmp_file "/tmp/ssh.exp.tmp";
    set hst_tmp_exst "$::env(HOME)/.ssh/known_hosts";
    if {[catch {
  set flp_tmp_temp [open ${ssh_tmp_file} w];
  set flp_tmp_host [open ${hst_tmp_exst} r];
  while 1 {
   gets ${flp_tmp_host} line;
   if [eof ${flp_tmp_host}] {
               break;
              }
              if [regexp "(\[^, ]+,)*${SSH_EXP_HST}(,\[^, ]+)* " ${line}] {
               continue;
              }
              puts ${flp_tmp_temp} ${line};
  }
  close ${flp_tmp_host};
  close ${flp_tmp_temp};
  send_user "${::SSH_EXP_INF}OK\n";
  file rename -force ${ssh_tmp_file} ${hst_tmp_exst};
    } error]} {
  fun_ssh_out_eror "${error}";
    }
}
#-----------------------------------------------
#print error and exit with code (1)
#-----------------------------------------------
proc fun_ssh_out_eror {ssh_out_eror} {
 if { "${ssh_out_eror}" == "" } {
  send_user "${::SSH_EXP_ERR}Usage:${::argv0} username/password@host\n";
 } else {
  send_user "${::SSH_EXP_ERR}${ssh_out_eror}\n";
 }
    exit 1;
}
#-----------------------------------------------
#main function
#-----------------------------------------------
proc fun_ssh_run_main {ssh_tmp_link} {
 fun_ssh_chk_parm "${ssh_tmp_link}";
 fun_ssh_chk_file;
 fun_ssh_mak_link;
}
#-----------------------------------------------
#check parameters and call main function
#-----------------------------------------------
if { [llength "${argv}"]!=1 } {
 fun_ssh_out_eror "";
} else {
 fun_ssh_run_main "[lindex "${argv}" 0]";
}
