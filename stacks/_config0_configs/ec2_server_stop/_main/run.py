def run(stackargs):

    stack = newStack(stackargs)

    stack.parse.add_required(key="hostname")

    stack.parse.add_required(key="time_increment",
                             default=30)

    # init the stack namespace
    stack.init_variables()

    # Check resource
    stack.get_resource(name=stack.hostname,
                       resource_type="server",
                       provider="ec2",
                       must_exists=True)

    # Stop the server when done to save money
    human_description = 'Stopping resource server hostname "{}"'.format(stack.hostname)
    stack.modify_resource(resource_type="server",
                          human_description=human_description,
                          provider="ec2",
                          name=stack.hostname,
                          method="stop")

    # sleep to make sure the server stopped
    human_description = "sleeping {}".format(stack.time_increment)
    stack.add_external_cmd(cmd="sleep {0}".format(stack.time_increment),
                           order_type="sleep::shellout",
                           human_description=human_description,
                           display=True,
                           role="external/cli/execute")

    return stack.get_results(zero_orders=True)
