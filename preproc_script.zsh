#!/bin/zsh

# Error handler function
handle_error() {
    print "Error executing Zsh function: $1"
    exit 1
}

# Set up trap to call the error handler on any ERR or EXIT signal
trap 'handle_error "$?"' ERR EXIT

function call_zsh_function {
    local input_file_path=$1
    local output_file_path=$2

    # Replace 'prepare_microbleednet_data' with your actual Zsh function and arguments
    local zsh_command="prepare_microbleednet_data ${input_file_path} ${output_file_path}>/dev/null || echo 'Error occurred'"
    print ${zsh_command}

    # Run the Zsh command and check the exit status
    if ! zsh -c "${zsh_command}"; then
        handle_error "Failed to execute Zsh command: ${zsh_command}"
    fi
}

function traverse_folder {
    local root_folder=$1
    local output_folder=$2
    local count=1

    for foldername in ${root_folder}/*/; do
        # Remove trailing slashes from foldername
        local sub_folder_name=$(basename "${foldername}")
        local parent_folder_path=$(dirname "${foldername}")
        local folder_path="${parent_folder_path}/${sub_folder_name}"

        for filepath in ${folder_path}/*(.); do
            local input_file_path=${filepath}
            local filename=$(basename "${filepath}")
            local output_file_path="${output_folder}/${sub_folder_name}/${filename:0:-7}"

            # Create the output directory if it doesn't exist
            mkdir -p ${output_folder}/${sub_folder_name}
            call_zsh_function ${input_file_path} ${output_file_path}

            # print "${output_file_path}\n"
            # print "${input_file_path}"
            ((count++))
        done
    done
}

# Use this when the root folder has only files
function traverse_folder_only_files {
    local root_folder=$1
    local output_folder=$2
    local count=1

    for filepath in ${root_folder}/*(.); do
        local input_file_path=${filepath}
        local filename=$(basename "${filepath}")
        local output_file_path="${output_folder}/${filename}"

        # Create the output directory if it doesn't exist
        mkdir -p ${output_folder}
        call_zsh_function ${input_file_path} ${output_file_path}

        ((count++))
    done
}

# Replace the paths with your actual paths
traverse_folder_only_files "/Users/rohanchhibba/Desktop/PreAD/Dataset/dataset2" "/Users/rohanchhibba/Desktop/PreAD/Dataset/dataset2_PreProc"

