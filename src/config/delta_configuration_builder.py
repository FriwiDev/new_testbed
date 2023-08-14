from config.configuration import Configuration


class DeltaConfigurationBuilder:

    @classmethod
    def get_delta(cls, destroy_config: Configuration, create_config: Configuration) -> Configuration:
        if len(destroy_config.start_instructions) > 0 or len(destroy_config.stop_instructions) > 0 or \
                len(create_config.start_instructions) > 0 or len(create_config.stop_instructions) > 0:
            raise Exception("Cannot build deltas for instructions")

        ret = Configuration()

        # Include all remove commands that are not present in new service to remove old components
        for x in destroy_config.stop_cmds:
            if x not in create_config.stop_cmds:
                ret.stop_cmds.append(x)

        # Add all required files
        ret.files = create_config.files

        # Include all start commands that are not present in old component to start things back up
        for x in create_config.start_cmds:
            if x not in destroy_config.start_cmds:
                ret.start_cmds.append(x)

        return ret
