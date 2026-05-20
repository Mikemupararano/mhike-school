import apiClient from "@/lib/api/client";

import {
    createTimetable,
    createTimetableAssignment,
    createTimetableEntry,
    createTimetablePeriod,
    getParentChildTimetable,
    getStudentTimetable,
    getTeacherTimetable,
    listTimetableAssignments,
    listTimetableEntries,
    listTimetablePeriods,
    listTimetables,
} from "./timetable";

jest.mock("@/lib/api/client", () => ({
    get: jest.fn(),
    post: jest.fn(),
}));

const mockedGet = apiClient.get as jest.Mock;
const mockedPost = apiClient.post as jest.Mock;

describe("timetable service", () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe("listTimetablePeriods", () => {
        it("fetches timetable periods", async () => {
            mockedGet.mockResolvedValue({
                data: [
                    {
                        id: 1,
                        name: "Period 1",
                    },
                ],
            });

            const result = await listTimetablePeriods();

            expect(mockedGet).toHaveBeenCalledWith(
                "/api/v1/timetables/periods"
            );

            expect(result).toHaveLength(1);
            expect(result[0].name).toBe("Period 1");
        });
    });

    describe("createTimetablePeriod", () => {
        it("creates a timetable period", async () => {
            mockedPost.mockResolvedValue({
                data: {
                    id: 1,
                    name: "Period 1",
                },
            });

            const payload = {
                name: "Period 1",
            };

            const result = await createTimetablePeriod(payload);

            expect(mockedPost).toHaveBeenCalledWith(
                "/api/v1/timetables/periods",
                payload
            );

            expect(result.id).toBe(1);
        });
    });

    describe("listTimetables", () => {
        it("fetches timetables with filters", async () => {
            mockedGet.mockResolvedValue({
                data: [],
            });

            const filters = {
                academic_year: "2025/2026",
            };

            await listTimetables(filters);

            expect(mockedGet).toHaveBeenCalledWith(
                "/api/v1/timetables",
                {
                    params: filters,
                }
            );
        });
    });

    describe("createTimetable", () => {
        it("creates a timetable", async () => {
            mockedPost.mockResolvedValue({
                data: {
                    id: 1,
                    name: "Main Timetable",
                },
            });

            const payload = {
                name: "Main Timetable",
            };

            const result = await createTimetable(payload);

            expect(mockedPost).toHaveBeenCalledWith(
                "/api/v1/timetables",
                payload
            );

            expect(result.name).toBe("Main Timetable");
        });
    });

    describe("listTimetableEntries", () => {
        it("fetches timetable entries", async () => {
            mockedGet.mockResolvedValue({
                data: [],
            });

            const filters = {
                class_group_id: 1,
            };

            await listTimetableEntries(filters);

            expect(mockedGet).toHaveBeenCalledWith(
                "/api/v1/timetables/entries",
                {
                    params: filters,
                }
            );
        });
    });

    describe("createTimetableEntry", () => {
        it("creates timetable entry", async () => {
            mockedPost.mockResolvedValue({
                data: {
                    id: 1,
                    title: "Physics",
                },
            });

            const payload = {
                title: "Physics",
            };

            const result = await createTimetableEntry(payload);

            expect(mockedPost).toHaveBeenCalledWith(
                "/api/v1/timetables/entries",
                payload
            );

            expect(result.title).toBe("Physics");
        });
    });

    describe("getTeacherTimetable", () => {
        it("fetches teacher timetable", async () => {
            mockedGet.mockResolvedValue({
                data: [],
            });

            await getTeacherTimetable("monday");

            expect(mockedGet).toHaveBeenCalledWith(
                "/api/v1/timetables/teacher/me",
                {
                    params: {
                        day_of_week: "monday",
                    },
                }
            );
        });
    });

    describe("getStudentTimetable", () => {
        it("fetches student timetable", async () => {
            mockedGet.mockResolvedValue({
                data: [],
            });

            await getStudentTimetable(1, "monday");

            expect(mockedGet).toHaveBeenCalledWith(
                "/api/v1/timetables/student/me",
                {
                    params: {
                        class_group_id: 1,
                        day_of_week: "monday",
                    },
                }
            );
        });
    });

    describe("getParentChildTimetable", () => {
        it("fetches parent child timetable", async () => {
            mockedGet.mockResolvedValue({
                data: [],
            });

            await getParentChildTimetable(10, 1, "monday");

            expect(mockedGet).toHaveBeenCalledWith(
                "/api/v1/timetables/parent/child/10",
                {
                    params: {
                        class_group_id: 1,
                        day_of_week: "monday",
                    },
                }
            );
        });
    });

    describe("listTimetableAssignments", () => {
        it("fetches timetable assignments", async () => {
            mockedGet.mockResolvedValue({
                data: [],
            });

            const filters = {
                assignment_type: "teacher",
            };

            await listTimetableAssignments(filters);

            expect(mockedGet).toHaveBeenCalledWith(
                "/api/v1/timetables/assignments",
                {
                    params: filters,
                }
            );
        });
    });

    describe("createTimetableAssignment", () => {
        it("creates timetable assignment", async () => {
            mockedPost.mockResolvedValue({
                data: {
                    id: 1,
                    assignment_type: "teacher",
                },
            });

            const payload = {
                assignment_type: "teacher",
            };

            const result = await createTimetableAssignment(payload);

            expect(mockedPost).toHaveBeenCalledWith(
                "/api/v1/timetables/assignments",
                payload
            );

            expect(result.assignment_type).toBe("teacher");
        });
    });
});