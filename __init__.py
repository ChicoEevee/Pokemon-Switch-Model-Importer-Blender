def attempt_install_flatbuffers(operator: bpy.types.Operator, context: bpy.types.Context) -> bool:
    """
    Attempts installing flatbuffers library if it's not installed using pip.
    :return: True if flatbuffers was found or successfully installed, False otherwise.
    """
    if are_flatbuffers_installed():
        return True
    if bpy.app.version >= (4, 2, 0) and not bpy.app.online_access:
        msg = "Can't install flatbuffers library using pip - Internet access is not allowed."
        operator.report({"INFO"}, msg)
        return False
    modules_path = bpy.utils.user_resource("SCRIPTS", path="modules", create=True)
    site.addsitedir(modules_path)
    context.window_manager.progress_begin(0, 3)
    ensurepip.bootstrap()
    context.window_manager.progress_update(1)
    subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    context.window_manager.progress_update(2)
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "--target", modules_path,
             "flatbuffers"])
    except subprocess.SubprocessError as e:
        context.window_manager.progress_update(3)
        context.window_manager.progress_end()
        msg = (f"Failed to install flatbuffers library using pip. {e}\n"
               f"To use this addon, put Python flatbuffers library folder for your platform"
               f"to this path: {modules_path}.")
        operator.report({"INFO"}, msg)
        return False
    context.window_manager.progress_update(3)
    context.window_manager.progress_end()
    if are_flatbuffers_installed():
        msg = "Successfully installed flatbuffers library."
        operator.report({"INFO"}, msg)



        return True
    msg = ("Failed to install flatbuffers library using pip."
           f"To use this addon, put Python flatbuffers library folder for your platform"
           f"to this path: {modules_path}.")
    operator.report({"ERROR"}, msg)




    return False