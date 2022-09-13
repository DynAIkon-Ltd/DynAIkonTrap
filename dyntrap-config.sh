#!/bin/bash 
VERSION=$(cat VERSION)
TITLE=$"DynAIkonTrap v$VERSION configuration tool"
BACKTILE=$"DynAIkon Ltd. 2022"
ADVANCED=$"ADVANCED"
INTERACTIVE=True
. ./venv/bin/activate

func_set_setting(){
  setting_name=$1
  setting_value=$2
  python3 -c "from DynAIkonTrap.settings import set_setting; set_setting(\"$setting_name\", \"$setting_value\")" 
}

func_get_setting(){
  setting_name=$1
  setting_value=$(python3 -c "from DynAIkonTrap.settings import get_setting; print(get_setting(\"$setting_name\"))")
}

calc_wt_size() {
  # NOTE: it's tempting to redirect stderr to /dev/null, so supress error 
  # output from tput. However in this case, tput detects neither stdout or 
  # stderr is a tty and so only gives default 80, 24 values
  WT_HEIGHT=18
  WT_WIDTH=$(tput cols)

  if [ -z "$WT_WIDTH" ] || [ "$WT_WIDTH" -lt 60 ]; then
    WT_WIDTH=80
  fi
  if [ "$WT_WIDTH" -gt 178 ]; then
    WT_WIDTH=120
  fi
  WT_MENU_HEIGHT=$(($WT_HEIGHT-7))
}


do_about() {
  whiptail --msgbox "\
Welcome to the DynAIkonTrap configuration tool. \n\n\
 - Use this to tune the system, configure settings and manage outputs. \n\n\
 - Navigate through the menus using the keyboard arrows ( ← ↑ ↓ → ) \n\n\
 - Select items with the ENTER key \n\n\
 - Enter values with the keyboard when prompted\n\n\n\
\
Note: Options marked \"ADVANCED\" are not reccomended to change as they may break system. \n\
" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT
  return 0
}

do_pipeline_menu(){
   FUN=$(whiptail --title "Pipeline Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --cancel-button Back --ok-button Select \
    "P1 LEGACY" "Use legacy pipeline, built on per-frame classification" \
    "P2 LOW_POWERED" "Use low-powered pipeline, suitable for lower-end RPi devices." \
    3>&1 1>&2 2>&3)
  RET=$?
  if [ $RET -eq 1 ]; then
    return 0
  elif [ $RET -eq 0 ]; then
    case "$FUN" in
      P1\ *) 
        func_set_setting "settings.pipeline.pipeline_variant" "0" 
        ;;
      P2\ *)
        func_set_setting "settings.pipeline.pipeline_variant" "1" 
        ;;
      *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
    esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
  fi
}

do_camera_menu(){
  FUN=$(whiptail --title "Camera Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --backtitle "$BACKTITLE" --cancel-button Back --ok-button Select \
    "C1 FRAMERATE     ($ADVANCED)" "Configure the camera framerate" \
    "C2 RESOLUTION    ($ADVANCED)" "Configure the camera resolutiton" \
    3>&1 1>&2 2>&3)
    RET=$?
    if [ $RET -eq 1 ]; then
      return 0
    elif [ $RET -eq 0 ]; then
      
      case "$FUN" in
        C1\ *) 
          func_get_setting "settings.camera.framerate"
          current_framerate=$setting_value
          selected_framerate=$(whiptail --title $ADVANCED --inputbox "Enter Desired Framerate (FPS): reccomended max. value: 20" \
          20 70 -- "$current_framerate" 3>&1 1>&2 2>&3)
          RET=$?
          if [ $RET -eq 0 ]; then
            func_set_setting "settings.camera.framerate" "$selected_framerate"
          fi 
          ;;
        C2\ *) 
          func_get_setting "settings.camera.resolution[0]"
          current_width=$setting_value
          selected_width=$(whiptail --title $ADVANCED --inputbox "Enter Desired Frame Width (PIXELS): reccomended max. value: 1920 " \
            20 70 -- "$current_width" 3>&1 1>&2 2>&3)
          if [ $? -eq 1 ]; then selected_width=$current_width; fi
          func_get_setting "settings.camera.resolution[1]" 
          current_height=$setting_value
          selected_height=$(whiptail --title $ADVANCED --inputbox "Enter Desired Frame Height (PIXELS): reccomended max. value: 1080" \
            20 70 -- "$current_height" 3>&1 1>&2 2>&3)
          resolution="($selected_width,$selected_height)"
          if [ $? -eq 0 ]; then
            func_set_setting "settings.camera.resolution" "$resolution"
          fi
          ;;
        *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
      esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
    fi
}

do_motion_menu(){
  FUN=$(whiptail --title "Motion Filter Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --backtitle "$BACKTITLE" --cancel-button Back --ok-button Select \
    "M1 MOVEMENT  " "Configure the animal movement parameters" \
    "M2 FILTER    " "Configure the filter parameters" \
  3>&1 1>&2 2>&3)
  RET=$?
  if [ $RET -eq 1 ]; then
    return 0
  elif [ $RET -eq 0 ]; then    
    case "$FUN" in
      M1\ *)
      do_motion_menu_movement
      ;;

      M2\ *)
      do_motion_menu_filter
      ;;
      *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
    esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
  fi
}

do_motion_menu_movement(){
  FUN=$(whiptail --title "Animal Movement Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --backtitle "$BACKTITLE" --cancel-button Back --ok-button Select \
    "AM1 AREA                    " "Configure the visible animal area to trigger" \
    "AM2 DISTANCE                " "Configure the distance of the animal from the camera" \
    "AM3 SPEED                   " "Configure the trigger speed of animal movement" \
    "AM4 FOCAL LENGTH ($ADVANCED)" "Configure the camera focal length" \
    "AM5 PIXEL SIZE   ($ADVANCED)" "Configure the pixel size " \
    "AM6 NR. PIXELS   ($ADVANCED)" "Configure the nr. of pixels on the sensor width" \
  3>&1 1>&2 2>&3)
  RET=$?
  if [ $RET -eq 1 ]; then
    return 0
  elif [ $RET -eq 0 ]; then
    case "$FUN" in
      AM1\ *)
      func_get_setting "settings.filter.motion.area_reality"
      current_area=$setting_value
      selected_area=$(whiptail --inputbox "Enter the desired area of animal to trigger motion (m^2): \n\n - This is the size of animal in meters-squared, as seen by the camera.  " \
        20 70 -- "$current_area" 3>&1 1>&2 2>&3)
      func_set_setting "settings.filter.motion.area_reality" "$selected_area"
      ;;
      AM2\ *)
      func_get_setting "settings.filter.motion.subject_distance"
      current_distance=$setting_value
      selected_distance=$(whiptail --inputbox "Enter the distance of animal from the camera (m): \n\n - This is an estimate of how far away the animal to detect will be from the camera sensor. Measured in meters. " \
        20 70 -- "$current_distance" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.filter.motion.subject_distance" "$selected_distance"
      fi
      ;;
      AM3\ *)
      func_get_setting "settings.filter.motion.animal_speed"
      current_speed=$setting_value
      selected_speed=$(whiptail --inputbox "Enter the speed of the animal moving past the camera (m/s): \n\n - This is an estimate of how fast the animal to detect will be moving through the camera field-of-view. Measured in meters-per-second (m/s)." \
        20 70 -- "$current_speed" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.filter.motion.animal_speed" "$selected_speed"
      fi
      ;;
      AM4\ *)
      func_get_setting "settings.filter.motion.focal_len"
      current_focal_len=$setting_value
      selected_focal_len=$(whiptail --title $ADVANCED --inputbox "Enter the focal length of your camera lens (m): \n\n - Estimate of your camera's focal length. Measured in meters (m)." \
        20 70 -- "$current_focal_len" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.filter.motion.focal_len" "$selected_focal_len"
      fi
      ;;
      AM5\ *)
      func_get_setting "settings.filter.motion.pixel_size"
      current_pixel_size=$setting_value
      selected_pixel_size=$(whiptail --title $ADVANCED --inputbox "Enter the size of the pixels on your camera sensor (m): \n\n - Estimate of your camera's pixel diameter. Measured in meters (m)." \
        20 70 -- "$current_pixel_size" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.filter.motion.pixel_size" "$selected_pixel_size"
      fi
      ;;
      AM6\ *)
      func_get_setting "settings.filter.motion.num_pixels"
      current_num_pixels=$setting_value
      selected_num_pixels=$(whiptail --title $ADVANCED --inputbox "Enter the number of pixels that make up the width of the sensor: \n\n" \
        20 70 -- "$current_num_pixels" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.filter.motion.num_pixels" "$selected_num_pixels"
      fi
      ;;
      *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
    esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
    #now update the smoothing factor (it's dependent on the IIR cutoff frequency)
    func_set_setting "settings.filter.processing.smoothing_factor" "1 / settings.filter.motion.iir_cutoff_hz"
  fi
}

do_motion_menu_filter(){
  FUN=$(whiptail --title "Motion Filter Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --backtitle "$BACKTITLE" --cancel-button Back --ok-button Select \
    "MF1 SMALL THRESHOLD           " "Configure small SoTV threshold" \
    "MF2 IIR ORDER      ($ADVANCED)" "Configure the order of the IIR motion filter" \
    "MF3 IIR STOP BAND  ($ADVANCED)" "Configure the stop band attenuation of the IIR filter" \
  3>&1 1>&2 2>&3)
  RET=$?
  if [ $RET -eq 1 ]; then
    return 0
  elif [ $RET -eq 0 ]; then
    case "$FUN" in
      MF1\ *)
      func_get_setting "settings.filter.motion.small_threshold"
      current_small_threshold=$setting_value
      selected_small_threshold=$(whiptail --inputbox "Enter the small threshold for the SoTV method: \n\n - This is the initial threshold as applied to the Sum of Thresholded Vectors, reccomended value around 10." \
        20 70 -- "$current_small_threshold" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.filter.motion.small_threshold" "$selected_small_threshold"
      fi
      ;;
      MF2\ *)
      func_get_setting "settings.filter.motion.iir_order"
      current_iir_order=$setting_value
      selected_iir_order=$(whiptail --title $ADVANCED --inputbox "Enter the order of the IIR filter:" \
        20 70 -- "$current_iir_order" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.filter.motion.iir_order" "$selected_iir_order"
      fi
      ;;
      MF3\ *)
      func_get_setting "settings.filter.motion.iir_attenuation"
      current_iir_attenuation=$setting_value
      selected_iir_attenuation=$(whiptail --title $ADVANCED --inputbox "Enter the stop-band attenuation of the IIR filter (dB):" \
        20 70 -- "$current_iir_attenuation" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.filter.motion.iir_attenuation" "$selected_iir_attenuation"
      fi
      ;;
      *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
    esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
  fi
}

do_animal_menu(){
      FUN=$(whiptail --menu "Choose a neural network to use from three pre-trained models:" 20 60 10 \
      "N1" "SSDLiteMobileNetv2-Animal-Only"\
      "N2" "SSDLiteMobileNetv2-Human-Animal"\
      "N3" "YOLOv4-tiny-Animal-Only"\
      "N4" "FASTCAT-Cloud Detection"\
      3>&1 1>&2 2>&3)
      RET=$?
      if [ $RET -eq 1 ]; then
      return 0
      elif [ $RET -eq 0 ]; then
        case "$FUN" in
        N1|N2|N3)    
          func_get_setting "settings.filter.animal.animal_threshold"
          thres="$setting_value"     
          func_set_setting "settings.filter.animal.detect_humans" "False"
          if [[ "$FUN" == "N1"  ||  "$FUN" == "N2" ]]; then 
              func_set_setting "settings.filter.animal.fast_animal_detect" "True"
          else
              func_set_setting "settings.filter.animal.fast_animal_detect" "False"
              thres="0.5" #set a better default threshold for YOLO detector -- pretty hacky! 
          fi
          selected_animal_thres=$(whiptail --inputbox "Enter Animal Threshold [Range 0 - 1]: \n\n - This is the confidence level required for the neural network to classify an animal. \n\n - Lower values capture more animals at the expense of false positives and vice versa." \
            20 70 -- $thres 3>&1 1>&2 2>&3) 
          if [ $? -eq 0 ]; then
            func_set_setting "settings.filter.animal.animal_threshold" "$selected_animal_thres"
          fi 
          ;;&
        N2) 
          func_set_setting "settings.filter.animal.detect_humans" "True"
          func_get_setting "settings.filter.animal.human_threshold" 
          current_human_thres="$setting_value"
          selected_human_thres=$(whiptail --inputbox "Enter Human Threshold (Range 0 - 1):  - This is the confidence level required for the neural network to classify a human. \n\n - Lower values detect humans more easily at the expense of accidental human detection and vice versa." \
          20 70 -- $current_human_thres 3>&1 1>&2 2>&3)
          RET=$?
          if [ $RET -eq 0 ]; then
            func_set_setting "settings.filter.animal.human_threshold" "$selected_human_threshold"
          fi
          ;;&
        N4) 
          whiptail --title "FASTCAT-Cloud Detection" --yesno "Would you like to use FASTCAT-Cloud to perform animal detection?" 8 78 --no-button "NO" --yes-button "YES"
          if [ $? -eq 0 ]; then 
            func_set_setting "settings.filter.animal.fastcat_cloud_detect" "True"
          else 
            func_set_setting "settings.filter.animal.fastcat_cloud_detect" "False"
          fi
         ;;
        esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
    fi
}

do_filter_menu(){
  FUN=$(whiptail --title "Filtering Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --backtitle "$BACKTITLE" --cancel-button Back --ok-button Select \
    "F1 MOTION    " "Configure the motion filter" \
    "F2 ANIMAL    " "Configure the animal filter" \
    "F3 PROCESSING" "Configure the filter processing" \
    3>&1 1>&2 2>&3)
    RET=$?
    if [ $RET -eq 1 ]; then
      return 0
    elif [ $RET -eq 0 ]; then
      case "$FUN" in
        F1\ *) 
          do_motion_menu 
          ;;
        F2\ *) 
          do_animal_menu 
          ;;
        F3\ *)
          do_processing_menu
          ;;
        *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
      esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
    fi
}

do_processing_menu(){
   FUN=$(whiptail --title "Processing Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --backtitle "$BACKTITLE" --cancel-button Back --ok-button Select \
    "P1 DETECTOR FRACTION                " "Configure the detector fraction" \
    "P2 CONTEXT BUFFER LEN.   ($ADVANCED)" "Configure the context buffer" \
    "P3 MOTION SEQ. MAX LEN.  ($ADVANCED)" "Configure the motion sequence length" \
    3>&1 1>&2 2>&3)
    RET=$?
    if [ $RET -eq 1 ]; then
      return 0
    elif [ $RET -eq 0 ]; then
      case "$FUN" in
        P1\ *)
        func_get_setting "settings.filter.processing.detector_fraction"
        current_detector_fraction=$setting_value
        selected_detector_fraction=$(whiptail --inputbox "Enter detector fraction (Range 0 - 1): \n\n - This is the maximum portion of a motion event processed with the low-powered pipeline. \n\n - Larger values will investigate videos more closely, spending more network inferences. Smaller values will process events more quickly. \n\n - The special value of 0.0 runs a single inference in the center frame only. \n\n - A good reccomended value for RPi 4 execution is 1.0, for less powerful RPis - such as the Zero W, try 0.25 \n\n - You can read more about how the low-powered pipeline works at: https://dynaikon.com/trap-docs/user-docs/how-it-works/low-powered.html \n\nEnter Value: "\
          25 90 -- "$current_detector_fraction" 3>&1 1>&2 2>&3)
        if [ $? -eq 0 ]; then
          func_set_setting "settings.filter.processing.detector_fraction" "$selected_detector_fraction"
        fi 
        ;;
        P2\ *)
        func_get_setting "settings.filter.processing.context_length_s"
        current_context_len=$setting_value
        selected_context_len_s=$(whiptail --title $ADVANCED --inputbox "Enter Context Length (s): \n\n - This is the context length the camera will use. \n\n - The amount the camera will continue recording pre and post animal visit. \n\n - Measured in seconds (s). "\
          20 70 -- "$current_context_len" 3>&1 1>&2 2>&3)
        if [ $? -eq 0 ]; then
          func_set_setting "settings.filter.processing.context_length" "$selected_context_lens_s"
        fi 
        ;;
        P3\ *)
        func_get_setting "settings.filter.processing.max_sequence_period_s"
        current_seq_period=$setting_value
        selected_seq_period=$(whiptail --title $ADVANCED --inputbox "Enter Max. Sequence Period Length (s): \n\n - This is the maximum length of time to record a sequence for. \n\n - Measured in seconds (s). "\
          20 70 -- "$current_seq_period" 3>&1 1>&2 2>&3)
        if [ $? -eq 0 ]; then
          func_set_setting "settings.filter.processing.max_sequence_period_s" "$selected_seq_period"
        fi 
        ;;
        *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
      esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
  fi
}

do_sensor_menu(){
   FUN=$(whiptail --title "Sensor Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --backtitle "$BACKTITLE" --cancel-button Back --ok-button Select \
    "S1 BOARD PORT      " "Configure the sensor board port" \
    "S2 BAUD RATE       " "Configure the sensor baud rate" \
    "S3 READING INTERVAL" "Configure the sensor reading interval" \
    "S4 GPS OBFUSCATION " "Configure the GPS obfuscation distance" \
    3>&1 1>&2 2>&3)
    RET=$?
    if [ $RET -eq 1 ]; then
      return 0
    elif [ $RET -eq 0 ]; then
      case "$FUN" in
        S1\ *)
        func_get_setting "settings.sensor.port" 
        current_port=$setting_value
        selected_port=$(whiptail --inputbox "Enter USB port attached to the sensor: "\
          20 70 -- "$current_port" 3>&1 1>&2 2>&3)
        if [ $? -eq 0 ]; then
          echo "$selected_port"
          func_set_setting "settings.sensor.port" \'$selected_port\'
        fi 
        ;;
        S2\ *)
        func_get_setting "settings.sensor.baud" 
        current_baud=$setting_value
        selected_baud=$(whiptail  --inputbox "Enter baud rate for the sensor serial connection: "\
          20 70 -- "$current_baud" 3>&1 1>&2 2>&3)
        if [ $? -eq 0 ]; then
          func_set_setting "settings.sensor.baud" "$selected_baud"
        fi 
        ;;
        S3\ *)
        func_get_setting "settings.sensor.interval_s" 
        current_interval=$setting_value
        selected_interval=$(whiptail --inputbox "Enter desired interval between sensor readings: \n\n - Measured in seconds (s). "\
          20 70 -- "$current_interval" 3>&1 1>&2 2>&3)
        if [ $? -eq 0 ]; then
          func_set_setting "settings.sensor.interval_s" "$selected_interval"
        fi 
        ;;
        S4\ *)
        func_get_setting "settings.sensor.obfuscation_distance_km" 
        current_obfuscation=$setting_value
        selected_obfuscation=$(whiptail --inputbox "Enter desired obfuscation distance for sensor readings: \n\n - Measured in kilometers (km). "\
          20 70 -- "$current_obfuscation" 3>&1 1>&2 2>&3)
        if [ $? -eq 0 ]; then
          func_set_setting "settings.sensor.obfuscation_distance_km" "$selected_obfuscation"
        fi 
        ;;
        *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
      esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
  fi
}

do_output_menu(){
  FUN=$(whiptail --title "Output Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --backtitle "$BACKTITLE" --cancel-button Back --ok-button Select \
    "O1 PATH           " "Change the output path" \
    "O2 FORMAT         " "Configure the output format" \
    "O3 FASTCAT-Cloud  " "Output to FASTCAT-Cloud" \
    "O4 DEVICE ID      " "Set your device ID" \
    "O5 DELETE METADATA" "Configure your device metadata" \
    3>&1 1>&2 2>&3)
    RET=$?
    if [ $RET -eq 1 ]; then
      return 0
    elif [ $RET -eq 0 ]; then
      case "$FUN" in
      O1\ *)
      func_get_setting "settings.output.path" 
      current_path=$setting_value
      selected_path=$(whiptail --inputbox "Choose the directory where DynAIkonTrap dumps its detections."\
        20 70 -- "$current_path" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.output.path" \'"$selected_path"\'
      fi 
      ;;
      O2\ *)
      whiptail --title "Output Format" --yesno "Select output format" 8 78 --yes-button "Video" --no-button "Images"
      func_set_setting 'settings.output.output_format' "$?"
      ;;
      O3\ *)
      whiptail --title "FASTCAT-Cloud" --yesno "Would you like to upload observations to FASTCAT-Cloud" 8 78 --yes-button "YES" --no-button "NO" 
      ret=$? 
      if [ $ret -eq 0 ]; then
        func_set_setting "settings.output.output_mode" "1"
        func_set_setting "settings.output.is_fcc" "1"
        whiptail --msgbox "Set up FASTCAT-Cloud uploads. \n - Please remember to configure your user ID and API key." 20 60 1
      else
        func_set_setting "settings.output.output_mode" "0"
        func_set_setting "settings.output.is_fcc" "0"
      fi
      ;;
      O4\ *)
      func_get_setting "settings.output.device_id" 
      current_device_id=$setting_value
      selected_device_id=$(whiptail --inputbox "Enter a device ID number for this system"\
        20 70 -- "$current_device_id" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.output.device_id" "$selected_device_id"
      fi 
      ;;
      O5\ *)
      whiptail --title "Metadata" --yesno "Would you like to delete metadata used for processing observations?" 8 78 --no-button "NO" --yes-button "YES"
      if [ $? -eq 0 ]; then
        func_set_setting "settings.output.delete_metadata" "1"
      else
        func_set_setting "settings.output.delete_metadata" "0"
      fi
      ;;
      *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
      esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
  fi
}
do_logging_menu(){
  FUN=$(whiptail --title "Logging Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --backtitle "$BACKTITLE" --cancel-button Back --ok-button Select \
    "L1 LOG LEVEL           " "Configure the log level" \
    "L2 PATH                " "Configure the log file path" \
  3>&1 1>&2 2>&3)
  RET=$?
  if [ $RET -eq 1 ]; then
    return 0
  elif [ $RET -eq 0 ]; then
    case "$FUN" in
    L1\ *)
    LOG=$(whiptail --menu "Desired logger verbosity level:" 20 60 10 \
      "DEBUG" ""\
      "INFO" ""\
      "WARNING" ""\
      "ERROR" ""\
      3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then 
        func_set_setting 'settings.logging.level' \'$LOG\'
      fi
    ;;
    L2\ *)
    func_get_setting "settings.logging.path" 
    current_log_path=$setting_value
      selected_log_path=$(whiptail --inputbox "Change to a file path for DynAIkonTrap to log to a file. \n\n - Default: /dev/stdout logs to the terminal window"\
        20 70 -- "$current_log_path" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.logging.path" \'"$selected_log_path"\'
      fi     ;;
    *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
    esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
  fi
}

do_fastcat_cloud(){
  FUN=$(whiptail --title "FASTCAT-Cloud Options" --menu "" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --backtitle "$BACKTITLE" --cancel-button Back --ok-button Select \
    "FC1 USER ID       " "Configure your user ID" \
    "FC2 API KEY       " "Configure your API key" \
    "FC3 SERVER      ($ADVANCED)  " "Configure the server address" \
    "FC4 POST        ($ADVANCED)  " "Configure the API POST endpoint" \
  3>&1 1>&2 2>&3)
  RET=$?
    if [ $RET -eq 1 ]; then
      return 0
    elif [ $RET -eq 0 ]; then
      case "$FUN" in
      FC1\ *)
      func_get_setting "settings.output.userId" 
      current_user_id=$setting_value
      selected_user_id=$(whiptail --inputbox "Enter your FASTCAT-Cloud User ID \n\n - Can be found on your account page at: https://service.fastcat-cloud.org/account \n\n - TIP: Use CTRL+SHIFT+V to paste from your clipboard."\
        20 70 -- "$current_user_id" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.output.userId" \'"$selected_user_id"\'
      fi 
      ;;
      FC2\ *)
      func_get_setting "settings.output.apiKey" 
      current_api_key=$setting_value
      selected_api_key=$(whiptail --inputbox "Enter your FASTCAT-Cloud API Key \n\n - You can create a new API key at: https://service.fastcat-cloud.org/account - TIP: Use CTRL+SHIFT+V to paste from your clipboard."\
        20 70 -- "$current_api_key" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.output.apiKey" \'"$selected_api_key"\'
      fi 
      ;;
      FC3\ *)
      func_get_setting "settings.output.server" 
      current_server=$setting_value
      selected_server=$(whiptail --title $ADVANCED --inputbox "Enter the FASTCAT-Cloud Server Address \n\n - Nominally: https://backend.fastcat-cloud.org "\
        20 70 -- "$current_server" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.output.server" \'"$selected_server"\'
      fi 
      ;;
      FC4\ *)
      func_get_setting "settings.output.POST" 
      current_post=$setting_value
      selected_post=$(whiptail --title $ADVANCED --inputbox "Enter the FASTCAT-Cloud API observation post endpoint \n\n - Nominally: /api/v2/predictions/demo "\
        20 70 -- "$current_post" 3>&1 1>&2 2>&3)
      if [ $? -eq 0 ]; then
        func_set_setting "settings.output.POST" \'"$selected_post"\'
      fi 
      ;;
      *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
      esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
  fi
}

do_make_settings(){
  python3 -c "from DynAIkonTrap.settings import load_settings, save_settings; s = load_settings(); save_settings(s)" > /dev/null 2>&1
}

do_restore(){
  whiptail --title "Restore Defauts" --yesno "Would you like to restore the default settings? (erase changes)" 8 78 --no-button "NO" --yes-button "YES"
  if [ $? -eq 0 ]; then
    rm "DynAIkonTrap/settings.json"
  fi
  do_make_settings
}

# START
do_make_settings
calc_wt_size
do_about
#
# Interactive use loop
#
if [ "$INTERACTIVE" = True ]; then
  calc_wt_size
  while true; do
      FUN=$(whiptail --title "$TITLE" --backtitle "$BACKTITLE" --menu "Setup Options" $WT_HEIGHT $WT_WIDTH $WT_MENU_HEIGHT --cancel-button Finish --ok-button Select \
        "1 Pipeline Options" "Configure the processing pipeline" \
        "2 Camera Options    " "Configure camera settings" \
        "3 Filter Options    " "Configure filter settings" \
        "4 Sensor Options    " "Configure sensor settings" \
        "5 Output Options    " "Configure output settings" \
        "6 Logging Options   " "Configure logging settings" \
        "7 FASTCAT-Cloud     " "Configure FASTCAT-Cloud options"\
        "8 Restore Defaults  " "Restore default settings" \
        3>&1 1>&2 2>&3)
    RET=$?
    if [ $RET -eq 1 ]; then
      exit 0
    elif [ $RET -eq 0 ]; then
       case "$FUN" in
         1\ *) do_pipeline_menu ;;
         2\ *) do_camera_menu ;;
         3\ *) do_filter_menu ;;
         4\ *) do_sensor_menu ;;
         5\ *) do_output_menu ;;
         6\ *) do_logging_menu ;;
         7\ *) do_fastcat_cloud ;;
         8\ *) do_restore ;;
         *) whiptail --msgbox "Programmer error: unrecognized option" 20 60 1 ;;
       esac || whiptail --msgbox "There was an error running option $FUN" 20 60 1
    else
      exit 1
    fi
  done
fi
