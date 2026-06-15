from rasputin.server import mcp


def main():
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
