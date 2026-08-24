from pcradio_mcp import server


def tools_by_name():
    return {tool.name: tool for tool in server.mcp._tool_manager.list_tools()}


def test_server_instructions_explain_cross_tool_workflows_and_boundaries():
    instructions = " ".join(server.mcp.instructions.split()).casefold()
    required = (
        "one-based channel numbers", "opaque station ID", "latest alarms revision",
        "available", "Do not invent IDs or revisions", "OTA/firmware update",
        "single configured device",
    )
    assert all(term.casefold() in instructions for term in required)


def test_every_tool_has_a_substantive_description():
    tools = tools_by_name()
    assert len(tools) == 20
    assert all(tool.description and len(tool.description) >= 35 for tool in tools.values())


def test_every_tool_argument_is_described_in_the_published_schema():
    for tool in tools_by_name().values():
        properties = tool.parameters.get("properties", {})
        assert all(schema.get("description") for schema in properties.values()), tool.name


def test_alarm_schema_publishes_schedule_and_range_semantics():
    properties = tools_by_name()["create_pcradio_alarm"].parameters["properties"]
    assert properties["hour"]["minimum"] == 0
    assert properties["hour"]["maximum"] == 23
    assert properties["target_volume"]["maximum"] == 100
    assert "Sunday=1" in properties["weekdays"]["description"]
    assert "62 for weekdays" in properties["weekdays"]["description"]
    assert "YYYY-MM-DD" in properties["date"]["description"]


def test_identifier_and_number_arguments_are_not_ambiguous():
    tools = tools_by_name()
    main_channel = tools["play_pcradio"].parameters["properties"]["channel"]["description"]
    user_id = tools["play_pcradio_user_station"].parameters["properties"]["station_id"]["description"]
    revision = tools["delete_pcradio_alarm"].parameters["properties"]["revision"]["description"]
    assert "one-based" in main_channel.casefold()
    assert "not a station id" in main_channel.casefold()
    assert "opaque station id" in user_id.casefold()
    assert "latest alarms.revision" in revision.casefold()
