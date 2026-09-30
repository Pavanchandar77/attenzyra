document.addEventListener("DOMContentLoaded", function () {


    // ======================================================
    // LOGIN SHOW / HIDE PASSWORD
    // ======================================================

    const loginPassword =
        document.getElementById("password");

    const loginShowButton =
        document.getElementById("showPassword");


    if (
        loginPassword &&
        loginShowButton
    ) {

        loginShowButton.addEventListener(
            "click",
            function () {

                if (
                    loginPassword.type ===
                    "password"
                ) {

                    loginPassword.type =
                        "text";

                    loginShowButton.textContent =
                        "Hide";

                } else {

                    loginPassword.type =
                        "password";

                    loginShowButton.textContent =
                        "Show";
                }

            }
        );

    }


    // ======================================================
    // MULTI-SCHOOL LOGIN / BOSS ADMIN LOGIN
    // ======================================================

    const schoolOptions = document.querySelectorAll(".school-option");
    const schoolSlug = document.getElementById("school_slug");
    const accountType = document.getElementById("account_type");
    const selectedSchoolBox = document.getElementById("selectedSchoolBox");
    const selectedSchoolName = document.getElementById("selectedSchoolName");
    const loginSubmitButton = document.getElementById("loginSubmitButton");
    const bossLoginButton = document.getElementById("bossLoginButton");
    const bossLoginPanel = document.getElementById("bossLoginPanel");

    schoolOptions.forEach(function (option) {
        option.addEventListener("click", function () {
            schoolOptions.forEach(function (item) {
                item.classList.remove("selected");
                item.setAttribute("aria-pressed", "false");
            });

            option.classList.add("selected");
            option.setAttribute("aria-pressed", "true");

            if (schoolSlug) schoolSlug.value = option.dataset.schoolSlug || "";
            if (accountType) accountType.value = "school";
            if (selectedSchoolName) selectedSchoolName.textContent = option.dataset.schoolName || "";
            if (selectedSchoolBox) selectedSchoolBox.hidden = false;
            if (loginSubmitButton) {
                loginSubmitButton.disabled = false;
                loginSubmitButton.textContent = "LOGIN TO " + (option.dataset.schoolName || "SCHOOL").toUpperCase();
            }

            if (bossLoginPanel) bossLoginPanel.hidden = true;
            if (bossLoginButton) bossLoginButton.setAttribute("aria-expanded", "false");
        });
    });

    if (bossLoginButton && bossLoginPanel) {
        bossLoginButton.addEventListener("click", function () {
            const opening = bossLoginPanel.hidden;
            bossLoginPanel.hidden = !opening;
            bossLoginButton.setAttribute("aria-expanded", String(opening));
            bossLoginButton.classList.toggle("active", opening);

            if (opening) {
                schoolOptions.forEach(function (item) {
                    item.classList.remove("selected");
                    item.setAttribute("aria-pressed", "false");
                });
                if (selectedSchoolBox) selectedSchoolBox.hidden = true;
                if (schoolSlug) schoolSlug.value = "";
                if (accountType) accountType.value = "boss";
                if (loginSubmitButton) {
                    loginSubmitButton.disabled = true;
                    loginSubmitButton.textContent = "SELECT A SCHOOL TO CONTINUE";
                }
                const bossUsername = document.getElementById("bossUsername");
                if (bossUsername) bossUsername.focus();
            } else if (accountType) {
                accountType.value = "school";
            }
        });
    }

    const bossPassword = document.getElementById("bossPassword");
    const bossShowButton = document.getElementById("showBossPassword");
    if (bossPassword && bossShowButton) {
        bossShowButton.addEventListener("click", function () {
            const showing = bossPassword.type === "password";
            bossPassword.type = showing ? "text" : "password";
            bossShowButton.textContent = showing ? "Hide" : "Show";
        });
    }

    // ======================================================
    // STUDENT PASSWORD FIELDS
    // ======================================================

    const toggleButtons =
        document.querySelectorAll(
            ".toggle-field"
        );


    toggleButtons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    const input =
                        button.parentElement
                        .querySelector(
                            ".password-field"
                        );


                    if (!input) {
                        return;
                    }


                    if (
                        input.type ===
                        "password"
                    ) {

                        input.type =
                            "text";

                        button.textContent =
                            "Hide";

                    } else {

                        input.type =
                            "password";

                        button.textContent =
                            "Show";
                    }

                }
            );

        }
    );


    // ======================================================
    // MOBILE NAVIGATION
    // ======================================================

    const menuButton =
        document.getElementById(
            "menuButton"
        );

    const navLinks =
        document.getElementById(
            "navLinks"
        );


    if (
        menuButton &&
        navLinks
    ) {

        menuButton.addEventListener(
            "click",
            function () {

                navLinks.classList.toggle(
                    "show-menu"
                );

            }
        );

    }


    // ======================================================
    // CLOSE ALERT
    // ======================================================

    const closeButtons =
        document.querySelectorAll(
            ".close-alert"
        );


    closeButtons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    const alert =
                        button.parentElement;

                    if (alert) {
                        alert.remove();
                    }

                }
            );

        }
    );


    // ======================================================
    // STUDENT SEARCH
    // ======================================================

    const studentSearch =
        document.getElementById(
            "studentSearch"
        );


    if (studentSearch) {

        studentSearch.addEventListener(
            "input",
            function () {

                const search =
                    studentSearch.value
                    .toLowerCase()
                    .trim();


                const cards =
                    document.querySelectorAll(
                        ".student-attendance-card"
                    );


                let visible = 0;


                cards.forEach(
                    function (card) {

                        const name =
                            card.dataset.student
                            || "";

                        const admission =
                            card.dataset.admission
                            || "";


                        if (
                            name.includes(search)
                            ||
                            admission.includes(search)
                        ) {

                            card.style.display =
                                "flex";

                            visible++;

                        } else {

                            card.style.display =
                                "none";
                        }

                    }
                );


                const counter =
                    document.getElementById(
                        "studentCount"
                    );


                if (counter) {

                    counter.textContent =
                        visible;
                }

            }
        );

    }


    // ======================================================
    // DASHBOARD CHARTS
    // ======================================================

    if (
        document.getElementById(
            "monthlyAttendanceChart"
        )
    ) {

        loadAttendanceCharts();

    }


    // ======================================================
    // DASHBOARD AUTO REFRESH
    // ======================================================

    if (
        document.getElementById(
            "totalStudents"
        )
    ) {

        refreshDashboard();


        setInterval(
            refreshDashboard,
            30000
        );

    }


    // ======================================================
    // CLASS ATTENDANCE CHART
    // ======================================================

    if (
        document.getElementById(
            "classAttendanceChart"
        )
    ) {

        loadClassChart();

    }

});


// ==========================================================
// CONFIRM ATTENDANCE
// ==========================================================

function confirmAttendance() {

    const absent =
        document.querySelectorAll(
            'input[name="absent_students"]:checked'
        ).length;


    return confirm(
        "Save attendance?\n\n" +
        "Absent students: " +
        absent
    );
}


// ==========================================================
// DASHBOARD REFRESH
// ==========================================================

async function refreshDashboard() {

    try {

        const select =
            document.querySelector(
                'select[name="class_name"]'
            );


        let url =
            "/api/dashboard-summary";


        if (select && select.value) {

            url +=
                "?class_name=" +
                encodeURIComponent(
                    select.value
                );

        }


        const response =
            await fetch(url);


        if (!response.ok) {
            return;
        }


        const data =
            await response.json();


        const total =
            document.getElementById(
                "totalStudents"
            );

        const recorded =
            document.getElementById(
                "recordedToday"
            );

        const present =
            document.getElementById(
                "presentCount"
            );

        const absent =
            document.getElementById(
                "absentCount"
            );


        if (total) {
            total.textContent =
                data.total_students;
        }


        if (recorded) {
            recorded.textContent =
                data.recorded_today;
        }


        if (present) {
            present.textContent =
                data.present;
        }


        if (absent) {
            absent.textContent =
                data.absent;
        }

    } catch (error) {

        console.log(
            "Dashboard refresh error:",
            error
        );

    }
}


// ==========================================================
// LOAD MONTHLY + YEARLY CHARTS
// ==========================================================

async function loadAttendanceCharts() {

    try {

        const monthlyResponse =
            await fetch(
                "/api/monthly-class-attendance"
            );


        const yearlyResponse =
            await fetch(
                "/api/yearly-class-attendance"
            );


        if (
            !monthlyResponse.ok ||
            !yearlyResponse.ok
        ) {
            return;
        }


        const monthly =
            await monthlyResponse.json();


        const yearly =
            await yearlyResponse.json();


        drawBarChart(
            "monthlyAttendanceChart",
            monthly.labels,
            monthly.data,
            "Monthly Average Attendance (%)"
        );


        drawBarChart(
            "yearlyAttendanceChart",
            yearly.labels,
            yearly.data,
            "Yearly Average Attendance (%)"
        );


    } catch (error) {

        console.log(
            "Chart error:",
            error
        );

    }
}


// ==========================================================
// CLASS-WISE CHART
// ==========================================================

async function loadClassChart() {

    try {

        const response =
            await fetch(
                "/api/class-wise-summary"
            );


        if (!response.ok) {
            return;
        }


        const data =
            await response.json();


        const labels =
            data.map(
                row => row.class_name
            );


        const values =
            data.map(
                row => row.percentage
            );


        drawBarChart(
            "classAttendanceChart",
            labels,
            values,
            "Today's Attendance (%)"
        );


    } catch (error) {

        console.log(
            "Class chart error:",
            error
        );

    }
}


// ==========================================================
// SIMPLE BAR CHART
// Uses Chart.js loaded by CSS-independent HTML below.
// ==========================================================

function drawBarChart(
    canvasId,
    labels,
    values,
    label
) {

    const canvas =
        document.getElementById(
            canvasId
        );


    if (!canvas) {
        return;
    }


    if (
        typeof Chart ===
        "undefined"
    ) {

        loadChartLibrary(
            function () {

                drawBarChart(
                    canvasId,
                    labels,
                    values,
                    label
                );

            }
        );

        return;
    }


    if (canvas._chartInstance) {

        canvas._chartInstance.destroy();

    }


    canvas._chartInstance =
        new Chart(
            canvas,
            {
                type: "bar",

                data: {

                    labels: labels,

                    datasets: [
                        {
                            label: label,

                            data: values,

                            borderWidth: 1
                        }
                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio:
                        false,

                    scales: {

                        y: {

                            beginAtZero: true,

                            max: 100,

                            ticks: {

                                callback:
                                    function (value) {

                                        return value +
                                            "%";

                                    }

                            }

                        }

                    },

                    plugins: {

                        legend: {
                            display: false
                        }

                    }

                }

            }
        );

}


// ==========================================================
// LOAD CHART.JS
// ==========================================================

function loadChartLibrary(callback) {

    if (
        document.getElementById(
            "chartLibrary"
        )
    ) {

        return;

    }


    const script =
        document.createElement(
            "script"
        );


    script.id =
        "chartLibrary";


    script.src =
        "https://cdn.jsdelivr.net/npm/chart.js";


    script.onload =
        callback;


    document.body.appendChild(
        script
    );

}


// ==========================================================
// EDIT STUDENT
// ==========================================================

function editStudent(
    admissionNo,
    name,
    className
) {

    const modal =
        document.getElementById(
            "editModal"
        );


    const admission =
        document.getElementById(
            "editAdmission"
        );

    const nameInput =
        document.getElementById(
            "editName"
        );

    const classInput =
        document.getElementById(
            "editClass"
        );


    if (!modal) {
        return;
    }


    admission.value =
        admissionNo;

    nameInput.value =
        name;

    classInput.value =
        className;


    modal.classList.add(
        "show"
    );

}


// ==========================================================
// CLOSE EDIT MODAL
// ==========================================================

function closeEditModal() {

    const modal =
        document.getElementById(
            "editModal"
        );


    if (modal) {

        modal.classList.remove(
            "show"
        );

    }

}


// ==========================================================
// SAVE EDITED STUDENT
// ==========================================================

document.addEventListener(
    "submit",
    async function (event) {

        if (
            event.target.id !==
            "editStudentForm"
        ) {

            return;

        }


        event.preventDefault();


        const admission =
            document.getElementById(
                "editAdmission"
            ).value;


        const name =
            document.getElementById(
                "editName"
            ).value.trim();


        const className =
            document.getElementById(
                "editClass"
            ).value.trim();


        const formData =
            new FormData();


        formData.append(
            "name",
            name
        );


        formData.append(
            "class_name",
            className
        );


        try {

            const response =
                await fetch(
                    "/edit-student/" +
                    encodeURIComponent(
                        admission
                    ),
                    {
                        method: "POST",
                        body: formData
                    }
                );


            const data =
                await response.json();


            alert(
                data.message
            );


            if (data.success) {

                location.reload();

            }


        } catch (error) {

            alert(
                "Unable to update student."
            );

        }

    }
);


// ==========================================================
// DELETE STUDENT
// ==========================================================

async function deleteStudent(
    admissionNo
) {

    const confirmed =
        confirm(
            "Delete student " +
            admissionNo +
            "?"
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                "/delete-student/" +
                encodeURIComponent(
                    admissionNo
                ),
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        alert(
            data.message
        );


        if (data.success) {

            location.reload();

        }

    } catch (error) {

        alert(
            "Unable to delete student."
        );

    }

}
// attendora left dashboard menu
(function(){
  const side=document.getElementById('ATTENZYRASidebar'), open=document.getElementById('ATTENZYRAMenuTrigger'), close=document.getElementById('ATTENZYRAMenuClose'), overlay=document.getElementById('ATTENZYRASidebarOverlay');
  if(!side||!open) return;
  function hide(){side.classList.remove('open');overlay&&overlay.classList.remove('show');}
  open.addEventListener('click',()=>{side.classList.add('open');overlay&&overlay.classList.add('show');});
  close&&close.addEventListener('click',hide); overlay&&overlay.addEventListener('click',hide);
})();
